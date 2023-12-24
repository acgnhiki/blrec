import asyncio
import html
from contextlib import suppress
from decimal import Decimal
from threading import Lock
from typing import Iterator, List, Optional

from loguru import logger
from tenacity import AsyncRetrying, retry_if_not_exception_type, stop_after_attempt

from blrec import __github__, __prog__, __version__
from blrec.bili.live import Live
from blrec.core.models import GiftSendMsg, GuardBuyMsg, SuperChatMsg, UserToastMsg
from blrec.danmaku.io import DanmakuWriter
from blrec.danmaku.models import (
    Danmu,
    GiftSendRecord,
    GuardBuyRecord,
    Metadata,
    SuperChatRecord,
    UserToast,
)
from blrec.event.event_emitter import EventEmitter, EventListener
from blrec.exception import exception_callback, submit_exception
from blrec.logging.context import async_task_with_logger_context
from blrec.path import danmaku_path
from blrec.utils.mixins import SwitchableMixin

from .danmaku_receiver import DanmakuReceiver, DanmuMsg
from .statistics import Statistics
from .stream_recorder import StreamRecorder, StreamRecorderEventListener

__all__ = 'DanmakuDumper', 'DanmakuDumperEventListener'


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
        self._logger_context = {'room_id': live.room_id}
        self._logger = logger.bind(**self._logger_context)

        self._live = live
        self._stream_recorder = stream_recorder
        self._receiver = danmaku_receiver

        self.danmu_uname = danmu_uname
        self.record_gift_send = record_gift_send
        self.record_free_gifts = record_free_gifts
        self.record_guard_buy = record_guard_buy
        self.record_super_chat = record_super_chat

        self._lock: Lock = Lock()
        self._path: Optional[str] = None
        self._files: List[str] = []
        self._statistics = Statistics(interval=60)

    @property
    def danmu_total(self) -> int:
        return self._statistics.count

    @property
    def danmu_rate(self) -> float:
        return self._statistics.rate

    @property
    def elapsed(self) -> float:
        return self._statistics.elapsed

    @property
    def dumping_path(self) -> Optional[str]:
        return self._path

    def _do_enable(self) -> None:
        self._stream_recorder.add_listener(self)
        self._statistics.reset()
        self._logger.debug('Enabled danmaku dumper')

    def _do_disable(self) -> None:
        self._stream_recorder.remove_listener(self)
        asyncio.create_task(self._stop_dumping())
        self._statistics.freeze()
        self._logger.debug('Disabled danmaku dumper')

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
        with self._lock:
            self._delta: float = 0
            self._record_start_time: int = record_start_time
            self._stream_recording_interrupted: bool = False
            self._path = danmaku_path(video_path)
            self._files.append(self._path)
            await self._stop_dumping()
            self._start_dumping()

    async def on_video_file_completed(self, video_path: str) -> None:
        with self._lock:
            await self._stop_dumping()
            self._path = None

    async def on_stream_recording_interrupted(
        self, timestamp: float, duration: float
    ) -> None:
        self._interrupted_timestamp = timestamp
        self._duration = duration
        self._stream_recording_interrupted = True
        self._logger.debug(
            'Stream recording interrupted, '
            f'timestamp: {timestamp}, duration: {duration}'
        )

    async def on_stream_recording_recovered(self, timestamp: float) -> None:
        self._recovered_timestamp = timestamp
        self._delta += -float(
            Decimal(str(self._recovered_timestamp))
            - Decimal(str(self._interrupted_timestamp))
        )
        self._stream_recording_interrupted = False
        self._logger.debug(
            'Stream recording recovered, '
            f'timestamp: {timestamp}, delta: {self._delta}'
        )

    async def on_duration_lost(self, duration: float) -> None:
        self._logger.debug(f'Total duration lost: ≈ {(duration)} s')
        self._delta = -duration

    def _start_dumping(self) -> None:
        self._create_dump_task()

    async def _stop_dumping(self) -> None:
        if hasattr(self, '_dump_task'):
            await self._cancel_dump_task()
            del self._dump_task  # type: ignore

    def _create_dump_task(self) -> None:
        self._dump_task = asyncio.create_task(self._do_dump())
        self._dump_task.add_done_callback(exception_callback)

    async def _cancel_dump_task(self) -> None:
        self._dump_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._dump_task

    @async_task_with_logger_context
    async def _do_dump(self) -> None:
        assert self._path is not None
        self._logger.debug('Started dumping danmaku')

        try:
            async with DanmakuWriter(self._path) as writer:
                self._logger.info(f"Danmaku file created: '{self._path}'")
                await self._emit('danmaku_file_created', self._path)
                await writer.write_metadata(self._make_metadata())

                async for attempt in AsyncRetrying(
                    retry=retry_if_not_exception_type((asyncio.CancelledError)),
                    stop=stop_after_attempt(3),
                ):
                    with attempt:
                        try:
                            await self._dumping_loop(writer)
                        except Exception as e:
                            submit_exception(e)
                            raise
        finally:
            self._logger.info(f"Danmaku file completed: '{self._path}'")
            await self._emit('danmaku_file_completed', self._path)
            self._logger.debug('Stopped dumping danmaku')

    async def _dumping_loop(self, writer: DanmakuWriter) -> None:
        while True:
            msg = await self._receiver.get_message()

            if isinstance(msg, DanmuMsg):
                await writer.write_danmu(self._make_danmu(msg))
                self._statistics.submit(1)
            elif isinstance(msg, UserToastMsg):
                await writer.write_user_toast(self._make_user_toast(msg))
            elif isinstance(msg, GiftSendMsg):
                if not self.record_gift_send:
                    continue
                record = self._make_gift_send_record(msg)
                if not self.record_free_gifts and record.is_free_gift():
                    continue
                await writer.write_gift_send_record(record)
            elif isinstance(msg, GuardBuyMsg):
                if not self.record_guard_buy:
                    continue
                await writer.write_guard_buy_record(self._make_guard_buy_record(msg))
            elif isinstance(msg, SuperChatMsg):
                if not self.record_super_chat:
                    continue
                await writer.write_super_chat_record(self._make_super_chat_record(msg))
            else:
                self._logger.warning(f'Unsupported message type: {repr(msg)}')

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
        text = html.escape(text, quote=False)

        return Danmu(
            stime=self._calc_stime(msg.date / 1000),
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
            ts=self._calc_stime(msg.timestamp),
            uid=msg.uid,
            user=msg.uname,
            giftname=msg.gift_name,
            giftcount=msg.count,
            cointype=msg.coin_type,
            price=msg.price,
        )

    def _make_guard_buy_record(self, msg: GuardBuyMsg) -> GuardBuyRecord:
        return GuardBuyRecord(
            ts=self._calc_stime(msg.timestamp),
            uid=msg.uid,
            user=msg.uname,
            giftname=msg.gift_name,
            count=msg.count,
            price=msg.price,
            level=msg.guard_level,
        )

    def _make_super_chat_record(self, msg: SuperChatMsg) -> SuperChatRecord:
        return SuperChatRecord(
            ts=self._calc_stime(msg.timestamp),
            uid=msg.uid,
            user=msg.uname,
            price=msg.price * msg.rate,
            time=msg.time,
            message=msg.message,
        )

    def _make_user_toast(self, msg: UserToastMsg) -> UserToast:
        return UserToast(
            ts=self._calc_stime(msg.start_time),
            uid=msg.uid,
            user=msg.username,
            unit=msg.unit,
            count=msg.num,
            price=msg.price,
            role=msg.role_name,
            level=msg.guard_level,
            msg=msg.toast_msg,
        )

    def _calc_stime(self, timestamp: float) -> float:
        if self._stream_recording_interrupted:
            return self._duration
        else:
            return (
                max(
                    timestamp * 1000
                    - self._record_start_time * 1000
                    + self._delta * 1000,
                    0,
                )
            ) / 1000
