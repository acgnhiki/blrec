import html
import asyncio
import logging
from contextlib import suppress
from typing import Iterator, List


from .. import __version__, __prog__
from .danmaku_receiver import DanmakuReceiver, DanmuMsg
from .stream_recorder import StreamRecorder, StreamRecorderEventListener
from .statistics import StatisticsCalculator
from ..bili.live import Live
from ..exception import exception_callback
from ..path import danmaku_path
from ..danmaku.models import Metadata, Danmu
from ..danmaku.io import DanmakuWriter
from ..utils.mixins import SwitchableMixin
from ..logging.room_id import aio_task_with_room_id


__all__ = 'DanmakuDumper',


logger = logging.getLogger(__name__)


class DanmakuDumper(StreamRecorderEventListener, SwitchableMixin):
    def __init__(
        self,
        live: Live,
        stream_recorder: StreamRecorder,
        danmaku_receiver: DanmakuReceiver,
        *,
        danmu_uname: bool = False,
    ) -> None:
        super().__init__()

        self._live = live
        self._stream_recorder = stream_recorder
        self._receiver = danmaku_receiver

        self.danmu_uname = danmu_uname

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

    def _start_dumping(self) -> None:
        self._create_dump_task()

    async def _stop_dumping(self) -> None:
        await self._cancel_dump_task()

    def _create_dump_task(self) -> None:
        self._dump_task = asyncio.create_task(self._dump())
        self._dump_task.add_done_callback(exception_callback)

    async def _cancel_dump_task(self) -> None:
        self._dump_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._dump_task

    @aio_task_with_room_id
    async def _dump(self) -> None:
        logger.debug('Started dumping danmaku')
        self._calculator.reset()

        try:
            async with DanmakuWriter(self._path) as writer:
                logger.info(f"Danmaku file created: '{self._path}'")
                await writer.write_metadata(self._make_metadata())

                while True:
                    msg = await self._receiver.get_message()
                    await writer.write_danmu(self._make_danmu(msg))
                    self._calculator.submit(1)
        finally:
            logger.info(f"Danmaku file completed: '{self._path}'")
            logger.debug('Stopped dumping danmaku')
            self._calculator.freeze()

    def _make_metadata(self) -> Metadata:
        return Metadata(
            user_name=self._live.user_info.name,
            room_id=self._live.room_info.room_id,
            room_title=self._live.room_info.title,
            area=self._live.room_info.area_name,
            parent_area=self._live.room_info.parent_area_name,
            live_start_time=self._live.room_info.live_start_time,
            record_start_time=self._record_start_time,
            recorder=f'{__prog__} {__version__}',
        )

    def _make_danmu(self, msg: DanmuMsg) -> Danmu:
        stime = max((msg.date - self._record_start_time * 1000), 0) / 1000

        if self.danmu_uname:
            text = f'{msg.uname}: {msg.text}'
        else:
            text = msg.text
        text = html.escape(text)

        return Danmu(
            stime=stime,
            mode=msg.mode,
            size=msg.size,
            color=msg.color,
            date=msg.date,
            pool=msg.pool,
            uid=msg.uid,
            dmid=msg.dmid,
            text=text,
        )
