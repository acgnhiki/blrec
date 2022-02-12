import html
import asyncio
import logging
from contextlib import suppress
from typing import Iterator, List, Optional

from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    retry_if_not_exception_type,
)

from .. import __version__, __prog__, __github__
from .danmaku_receiver import DanmakuReceiver, DanmuMsg
from .stream_recorder import StreamRecorder, StreamRecorderEventListener
from .statistics import StatisticsCalculator
from ..bili.live import Live
from ..exception import exception_callback, submit_exception
from ..event.event_emitter import EventListener, EventEmitter
from ..path import danmaku_path
from ..core.models import GiftSendMsg, GuardBuyMsg, SuperChatMsg
from ..danmaku.models import (
    Metadata, Danmu, GiftSendRecord, GuardBuyRecord, SuperChatRecord
)
from ..danmaku.io import DanmakuWriter
from ..utils.mixins import SwitchableMixin
from ..logging.room_id import aio_task_with_room_id


__all__ = 'DanmakuDumper', 'DanmakuDumperEventListener'


logger = logging.getLogger(__name__)


class DanmakuDumperEventListener(EventListener):
    async def on_danmaku_file_created(self, path: str) -> None:
        ...

    async def on_danmaku_file_completed(self, path: str) -> None:
        ...


class DanmakuDumper(
    EventEmitter[DanmakuDumperEventListener],
    StreamRecorderEventListener,
    SwitchableMixin,
):
    def __init__(
        self,
        live: Live,
        stream_recorder: StreamRecorder,
        danmaku_receiver: DanmakuReceiver,
        *,
        danmu_uname: bool = False,
        record_gift_send: bool = False,
        record_free_gifts: bool = False,
        record_guard_buy: bool = False,
        record_super_chat: bool = False,
    ) -> None:
        super().__init__()

        self._live = live
        self._stream_recorder = stream_recorder
        self._receiver = danmaku_receiver

        self.danmu_uname = danmu_uname
        self.record_gift_send = record_gift_send
        self.record_free_gifts = record_free_gifts
        self.record_guard_buy = record_guard_buy
        self.record_super_chat = record_super_chat

        self._path: Optional[str] = None
        self._files: List[str] = []
        self._calculator = StatisticsCalculator(interval=60)

    @property
    def danmu_count(self) -> int:
        return self._calculator.count

    @property
    def danmu_rate(self) -> float:
        return self._calculator.rate

    @property
    def elapsed(self) -> float:
        return self._calculator.elapsed

    @property
    def dumping_path(self) -> Optional[str]:
        return self._path

    def _do_enable(self) -> None:
        self._stream_recorder.add_listener(self)
        logger.debug('Enabled danmaku dumper')

    def _do_disable(self) -> None:
        self._stream_recorder.remove_listener(self)
        logger.debug('Disabled danmaku dumper')

    def set_live_start_time(self, time: int) -> None:
        self._live_start_time = time

    def has_file(self) -> bool:
        return bool(self._files)

    def get_files(self) -> Iterator[str]:
        for file in self._files:
            yield file

    def clear_files(self) -> None:
        self._files.clear()

    async def on_video_file_created(
        self, video_path: str, record_start_time: int
    ) -> None:
        self._path = danmaku_path(video_path)
        self._record_start_time = record_start_time
        self._files.append(self._path)
        self._start_dumping()

    async def on_video_file_completed(self, video_path: str) -> None:
        await self._stop_dumping()
        self._path = None

    def _start_dumping(self) -> None:
        self._create_dump_task()

    async def _stop_dumping(self) -> None:
        await self._cancel_dump_task()

    def _create_dump_task(self) -> None:
        self._dump_task = asyncio.create_task(self._do_dump())
        self._dump_task.add_done_callback(exception_callback)

    async def _cancel_dump_task(self) -> None:
        self._dump_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._dump_task

    @aio_task_with_room_id
    async def _do_dump(self) -> None:
        assert self._path is not None
        logger.debug('Started dumping danmaku')
        self._calculator.reset()

        try:
            async with DanmakuWriter(self._path) as writer:
                logger.info(f"Danmaku file created: '{self._path}'")
                await self._emit('danmaku_file_created', self._path)
                await writer.write_metadata(self._make_metadata())

                async for attempt in AsyncRetrying(
                    retry=retry_if_not_exception_type((
                        asyncio.CancelledError
                    )),
                    stop=stop_after_attempt(3),
                ):
                    with attempt:
                        try:
                            await self._dumping_loop(writer)
                        except Exception as e:
                            submit_exception(e)
                            raise
        finally:
            logger.info(f"Danmaku file completed: '{self._path}'")
            await self._emit('danmaku_file_completed', self._path)
            logger.debug('Stopped dumping danmaku')
            self._calculator.freeze()

    async def _dumping_loop(self, writer: DanmakuWriter) -> None:
        while True:
            msg = await self._receiver.get_message()
            if isinstance(msg, DanmuMsg):
                await writer.write_danmu(self._make_danmu(msg))
                self._calculator.submit(1)
            elif isinstance(msg, GiftSendMsg):
                if not self.record_gift_send:
                    continue
                record = self._make_gift_send_record(msg)
                if (
                    not self.record_free_gifts and
                    record.is_free_gift()
                ):
                    continue
                await writer.write_gift_send_record(record)
            elif isinstance(msg, GuardBuyMsg):
                if not self.record_guard_buy:
                    continue
                await writer.write_guard_buy_record(
                    self._make_guard_buy_record(msg)
                )
            elif isinstance(msg, SuperChatMsg):
                if not self.record_super_chat:
                    continue
                await writer.write_super_chat_record(
                    self._make_super_chat_record(msg)
                )
            else:
                logger.warning('Unsupported message type:', repr(msg))

    def _make_metadata(self) -> Metadata:
        return Metadata(
            user_name=self._live.user_info.name,
            room_id=self._live.room_info.room_id,
            room_title=self._live.room_info.title,
            area=self._live.room_info.area_name,
            parent_area=self._live.room_info.parent_area_name,
            live_start_time=self._live.room_info.live_start_time,
            record_start_time=self._record_start_time,
            recorder=f'{__prog__} v{__version__} {__github__}',
        )

    def _make_danmu(self, msg: DanmuMsg) -> Danmu:
        if self.danmu_uname:
            text = f'{msg.uname}: {msg.text}'
        else:
            text = msg.text
        text = html.escape(text)

        return Danmu(
            stime=self._calc_stime(msg.date),
            mode=msg.mode,
            size=msg.size,
            color=msg.color,
            date=msg.date,
            pool=msg.pool,
            uid_hash=msg.uid_hash,
            uid=msg.uid,
            uname=msg.uname,
            dmid=msg.dmid,
            text=text,
        )

    def _make_gift_send_record(self, msg: GiftSendMsg) -> GiftSendRecord:
        return GiftSendRecord(
            ts=self._calc_stime(msg.timestamp * 1000),
            uid=msg.uid,
            user=msg.uname,
            giftname=msg.gift_name,
            giftcount=msg.count,
            cointype=msg.coin_type,
            price=msg.price,
        )

    def _make_guard_buy_record(self, msg: GuardBuyMsg) -> GuardBuyRecord:
        return GuardBuyRecord(
            ts=self._calc_stime(msg.timestamp * 1000),
            uid=msg.uid,
            user=msg.uname,
            giftname=msg.gift_name,
            count=msg.count,
            price=msg.price,
            level=msg.guard_level,
        )

    def _make_super_chat_record(self, msg: SuperChatMsg) -> SuperChatRecord:
        return SuperChatRecord(
            ts=self._calc_stime(msg.timestamp * 1000),
            uid=msg.uid,
            user=msg.uname,
            price=msg.price * msg.rate,
            time=msg.time,
            message=msg.message,
        )

    def _calc_stime(self, timestamp: int) -> float:
        return max((timestamp - self._record_start_time * 1000), 0) / 1000
