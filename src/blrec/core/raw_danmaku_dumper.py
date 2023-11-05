import asyncio
import json
from contextlib import suppress
from threading import Lock

import aiofiles
from aiofiles.threadpool.text import AsyncTextIOWrapper
from loguru import logger
from tenacity import AsyncRetrying, retry_if_not_exception_type, stop_after_attempt

from blrec.bili.live import Live
from blrec.event.event_emitter import EventEmitter, EventListener
from blrec.exception import exception_callback, submit_exception
from blrec.logging.context import async_task_with_logger_context
from blrec.path import raw_danmaku_path
from blrec.utils.mixins import SwitchableMixin

from .raw_danmaku_receiver import RawDanmakuReceiver
from .stream_recorder import StreamRecorder, StreamRecorderEventListener

__all__ = 'RawDanmakuDumper', 'RawDanmakuDumperEventListener'


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
        live: Live,
        stream_recorder: StreamRecorder,
        danmaku_receiver: RawDanmakuReceiver,
    ) -> None:
        super().__init__()
        self._logger_context = {'room_id': live.room_id}
        self._logger = logger.bind(**self._logger_context)
        self._stream_recorder = stream_recorder
        self._receiver = danmaku_receiver
        self._lock: Lock = Lock()

    def _do_enable(self) -> None:
        self._stream_recorder.add_listener(self)
        self._logger.debug('Enabled raw danmaku dumper')

    def _do_disable(self) -> None:
        self._stream_recorder.remove_listener(self)
        asyncio.create_task(self._stop_dumping())
        self._logger.debug('Disabled raw danmaku dumper')

    async def on_video_file_created(
        self, video_path: str, record_start_time: int
    ) -> None:
        with self._lock:
            self._path = raw_danmaku_path(video_path)
            await self._stop_dumping()
            self._start_dumping()

    async def on_video_file_completed(self, video_path: str) -> None:
        with self._lock:
            await self._stop_dumping()

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
        self._logger.debug('Started dumping raw danmaku')
        try:
            async with aiofiles.open(self._path, 'wt', encoding='utf8') as f:
                self._logger.info(f"Raw danmaku file created: '{self._path}'")
                await self._emit('raw_danmaku_file_created', self._path)

                async for attempt in AsyncRetrying(
                    retry=retry_if_not_exception_type((asyncio.CancelledError)),
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
            self._logger.info(f"Raw danmaku file completed: '{self._path}'")
            await self._emit('raw_danmaku_file_completed', self._path)
            self._logger.debug('Stopped dumping raw danmaku')

    async def _dumping_loop(self, file: AsyncTextIOWrapper) -> None:
        while True:
            danmu = await self._receiver.get_raw_danmaku()
            json_string = json.dumps(danmu, ensure_ascii=False)
            await file.write(json_string + '\n')
