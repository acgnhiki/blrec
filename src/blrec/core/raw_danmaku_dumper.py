import json
import asyncio
import logging
from contextlib import suppress

import aiofiles
from aiofiles.threadpool.text import AsyncTextIOWrapper
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    retry_if_not_exception_type,
)

from .raw_danmaku_receiver import RawDanmakuReceiver
from .stream_recorder import StreamRecorder, StreamRecorderEventListener
from ..exception import exception_callback, submit_exception
from ..event.event_emitter import EventListener, EventEmitter
from ..path import raw_danmaku_path
from ..utils.mixins import SwitchableMixin
from ..logging.room_id import aio_task_with_room_id


__all__ = 'RawDanmakuDumper', 'RawDanmakuDumperEventListener'


logger = logging.getLogger(__name__)


class RawDanmakuDumperEventListener(EventListener):
    async def on_raw_danmaku_file_created(self, path: str) -> None:
        ...

    async def on_raw_danmaku_file_completed(self, path: str) -> None:
        ...


class RawDanmakuDumper(
    EventEmitter[RawDanmakuDumperEventListener],
    StreamRecorderEventListener,
    SwitchableMixin,
):
    def __init__(
        self,
        stream_recorder: StreamRecorder,
        danmaku_receiver: RawDanmakuReceiver,
    ) -> None:
        super().__init__()
        self._stream_recorder = stream_recorder
        self._receiver = danmaku_receiver

    def _do_enable(self) -> None:
        self._stream_recorder.add_listener(self)
        logger.debug('Enabled raw danmaku dumper')

    def _do_disable(self) -> None:
        self._stream_recorder.remove_listener(self)
        logger.debug('Disabled raw danmaku dumper')

    async def on_video_file_created(
        self, video_path: str, record_start_time: int
    ) -> None:
        self._path = raw_danmaku_path(video_path)
        self._start_dumping()

    async def on_video_file_completed(self, video_path: str) -> None:
        await self._stop_dumping()

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
        logger.debug('Started dumping raw danmaku')
        try:
            async with aiofiles.open(self._path, 'wt', encoding='utf8') as f:
                logger.info(f"Raw danmaku file created: '{self._path}'")
                await self._emit('raw_danmaku_file_created', self._path)

                async for attempt in AsyncRetrying(
                    retry=retry_if_not_exception_type((
                        asyncio.CancelledError
                    )),
                    stop=stop_after_attempt(3),
                ):
                    with attempt:
                        try:
                            await self._dumping_loop(f)
                        except Exception as e:
                            submit_exception(e)
                            raise
                while True:
                    danmu = await self._receiver.get_raw_danmaku()
                    json_string = json.dumps(danmu, ensure_ascii=False)
                    await f.write(json_string + '\n')
        finally:
            logger.info(f"Raw danmaku file completed: '{self._path}'")
            await self._emit('raw_danmaku_file_completed', self._path)
            logger.debug('Stopped dumping raw danmaku')

    async def _dumping_loop(self, file: AsyncTextIOWrapper) -> None:
        while True:
            danmu = await self._receiver.get_raw_danmaku()
            json_string = json.dumps(danmu, ensure_ascii=False)
            await file.write(json_string + '\n')
