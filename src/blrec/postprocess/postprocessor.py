from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from pathlib import PurePath
from typing import Any, Awaitable, Dict, Final, Iterator, List, Optional, Tuple, Union

from loguru import logger
from reactivex.scheduler import ThreadPoolScheduler

from blrec.logging.context import async_task_with_logger_context

from ..bili.live import Live
from ..core import Recorder, RecorderEventListener
from ..event.event_emitter import EventEmitter, EventListener
from ..exception import exception_callback, submit_exception
from ..flv.helpers import is_valid_flv_file
from ..flv.metadata_analysis import analyse_metadata
from ..flv.metadata_injection import InjectingProgress, inject_metadata
from ..path import (
    extra_metadata_path,
    ffmpeg_metadata_path,
    playlist_path,
    record_metadata_path,
)
from ..utils.mixins import AsyncCooperationMixin, AsyncStoppableMixin, SupportDebugMixin
from .ffmpeg_metadata import make_metadata_file
from .helpers import discard_file, files_related, get_extra_metadata
from .models import DeleteStrategy, PostprocessorStatus
from .remux import RemuxingProgress, RemuxingResult, remux_video
from .typing import Progress

__all__ = (
    'Postprocessor',
    'PostprocessorEventListener',
    'PostprocessorStatus',
    'DeleteStrategy',
)


DISPLAY_PROGRESS = bool(os.environ.get('BLREC_PROGRESS'))


class PostprocessorEventListener(EventListener):
    async def on_video_postprocessing_completed(
        self, postprocessor: Postprocessor, path: str
    ) -> None:
        ...

    async def on_postprocessing_completed(
        self, postprocessor: Postprocessor, files: List[str]
    ) -> None:
        ...


class Postprocessor(
    EventEmitter[PostprocessorEventListener],
    RecorderEventListener,
    AsyncStoppableMixin,
    AsyncCooperationMixin,
    SupportDebugMixin,
):
    _worker_semaphore: Final = asyncio.Semaphore(value=1)

    def __init__(
        self,
        live: Live,
        recorder: Recorder,
        *,
        remux_to_mp4: bool = False,
        inject_extra_metadata: bool = False,
        delete_source: DeleteStrategy = DeleteStrategy.AUTO,
    ) -> None:
        super().__init__()
        self._init_for_debug(live.room_id)
        self._logger_context = {'room_id': live.room_id}
        self._logger = logger.bind(**self._logger_context)

        self._live = live
        self._recorder = recorder

        self.remux_to_mp4 = remux_to_mp4
        self.inject_extra_metadata = inject_extra_metadata
        self.delete_source = delete_source

        self._status = PostprocessorStatus.WAITING
        self._postprocessing_path: Optional[str] = None
        self._postprocessing_progress: Optional[Progress] = None
        self._completed_files: List[str] = []

    @property
    def recorder(self) -> Recorder:
        return self._recorder

    @property
    def status(self) -> PostprocessorStatus:
        return self._status

    @property
    def postprocessing_path(self) -> Optional[str]:
        return self._postprocessing_path

    @property
    def postprocessing_progress(self) -> Optional[Progress]:
        return self._postprocessing_progress

    def get_completed_files(self) -> Iterator[str]:
        yield from iter(self._completed_files)

    async def on_recording_started(self, recorder: Recorder) -> None:
        # clear completed files of previous recording
        self._completed_files.clear()

    async def on_video_file_completed(self, recorder: Recorder, path: str) -> None:
        self._queue.put_nowait(path)

    async def on_danmaku_file_completed(self, recorder: Recorder, path: str) -> None:
        self._completed_files.append(path)

    async def _do_start(self) -> None:
        self._recorder.add_listener(self)

        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._scheduler = ThreadPoolScheduler()
        self._task = asyncio.create_task(self._worker())
        self._task.add_done_callback(exception_callback)

        self._logger.debug('Started postprocessor')

    async def _do_stop(self) -> None:
        self._recorder.remove_listener(self)

        await self._queue.join()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task

        del self._queue
        del self._scheduler
        del self._task

        self._logger.debug('Stopped postprocessor')

    @async_task_with_logger_context
    async def _worker(self) -> None:
        while True:
            await self._postprocess()

    async def _postprocess(self) -> None:
        self._status = PostprocessorStatus.WAITING
        self._postprocessing_path = None
        self._postprocessing_progress = None

        video_path = await self._queue.get()
        self._completed_files.append(video_path)

        async with self._worker_semaphore:
            self._logger.debug(f'Postprocessing... {video_path}')
            await self._wait_for_metadata_file(video_path)

            try:
                _, ext = os.path.splitext(video_path)
                if ext == '.flv':
                    result_path = await self._process_flv(video_path)
                elif ext == '.m4s':
                    result_path = await self._process_m4s(video_path)
                else:
                    result_path = video_path

                if result_path != video_path:
                    self._completed_files.append(result_path)
                await self._emit('video_postprocessing_completed', self, result_path)

                files = [result_path, *files_related(result_path)]
                await self._emit('postprocessing_completed', self, files)
            except Exception as exc:
                submit_exception(exc)
            finally:
                self._queue.task_done()

    async def _process_flv(self, video_path: str) -> str:
        if not await self._is_vaild_flv_file(video_path):
            self._logger.warning(f'The flv file may be invalid: {video_path}')
            if os.path.getsize(video_path) < 1024**2:
                return video_path

        if self.remux_to_mp4:
            self._status = PostprocessorStatus.REMUXING
            result_path, remuxing_result = await self._remux_video_to_mp4(video_path)
            if not self._debug:
                if self._should_delete_source_files(remuxing_result):
                    await discard_file(video_path)
        elif self.inject_extra_metadata:
            self._status = PostprocessorStatus.INJECTING
            result_path = await self._inject_extra_metadata(video_path)
        else:
            result_path = video_path

        if not self._debug:
            await discard_file(extra_metadata_path(video_path), 'DEBUG')

        return result_path

    async def _process_m4s(self, video_path: str) -> str:
        if not self.remux_to_mp4:
            return video_path

        self._status = PostprocessorStatus.REMUXING
        result_path, remuxing_result = await self._remux_video_to_mp4(video_path)

        if not self._debug and self._should_delete_source_files(remuxing_result):
            await discard_file(video_path)
            await discard_file(playlist_path(video_path))
            await discard_file(record_metadata_path(video_path), 'DEBUG')
            await discard_file(ffmpeg_metadata_path(video_path), 'DEBUG')

        return result_path

    async def _inject_extra_metadata(self, path: str) -> str:
        self._logger.info(f"Injecting metadata for '{path}' ...")
        try:
            try:
                metadata = await get_extra_metadata(path)
            except Exception as e:
                self._logger.warning(f'Failed to get extra metadata: {repr(e)}')
                self._logger.info(f"Analysing metadata for '{path}' ...")
                await self._analyse_metadata(path)
                metadata = await get_extra_metadata(path)
            else:
                if 'keyframes' not in metadata:
                    self._logger.warning('The keyframes metadata lost')
                    self._logger.info(f"Analysing metadata for '{path}' ...")
                    await self._analyse_metadata(path)
                    new_metadata = await get_extra_metadata(path)
                    metadata.update(new_metadata)
            await self._inject_metadata(path, metadata)
        except Exception as e:
            self._logger.error(f"Failed to inject metadata for '{path}': {repr(e)}")
            submit_exception(e)
        else:
            self._logger.info(f"Successfully injected metadata for '{path}'")
        return path

    async def _remux_video_to_mp4(self, in_path: str) -> Tuple[str, RemuxingResult]:
        _, ext = os.path.splitext(in_path)

        if ext == '.flv':
            out_path = str(PurePath(in_path).with_suffix('.mp4'))
            metadata_path = await make_metadata_file(in_path)
        elif ext == '.m4s':
            _in_path = in_path
            in_path = playlist_path(in_path)
            out_path = str(PurePath(in_path).with_suffix('.mp4'))
            metadata_path = await make_metadata_file(_in_path)
        else:
            raise NotImplementedError(in_path)

        self._logger.info(f"Remuxing '{in_path}' to '{out_path}' ...")
        remux_result = await self._remux_video(in_path, out_path, metadata_path)

        if remux_result.is_failed():
            self._logger.error(f"Failed to remux '{in_path}' to '{out_path}'")
            result_path = _in_path if ext == 'm4s' else in_path
        elif remux_result.is_warned():
            self._logger.warning('Remuxing done, but ran into problems.')
            result_path = out_path
        elif remux_result.is_successful():
            self._logger.info(f"Successfully remuxed '{in_path}' to '{out_path}'")
            result_path = out_path
        else:
            pass

        self._logger.debug(f'ffmpeg output:\n{remux_result.output}')

        if not self._debug and ext == '.flv':
            await discard_file(metadata_path, 'DEBUG')

        return result_path, remux_result

    def _analyse_metadata(self, path: str) -> Awaitable[None]:
        future: asyncio.Future[None] = asyncio.Future()
        self._postprocessing_path = path

        subscription = analyse_metadata(
            path, display_progress=DISPLAY_PROGRESS
        ).subscribe(
            on_error=lambda e: future.set_exception(e),
            on_completed=lambda: future.set_result(None),
            scheduler=self._scheduler,
        )
        future.add_done_callback(lambda f: subscription.dispose())

        return future

    def _inject_metadata(self, path: str, metadata: Dict[str, Any]) -> Awaitable[None]:
        future: asyncio.Future[None] = asyncio.Future()
        self._postprocessing_path = path

        def on_next(value: InjectingProgress) -> None:
            self._postprocessing_progress = value

        subscription = inject_metadata(
            path, metadata, display_progress=DISPLAY_PROGRESS
        ).subscribe(
            on_next=on_next,
            on_error=lambda e: future.set_exception(e),
            on_completed=lambda: future.set_result(None),
            scheduler=self._scheduler,
        )
        future.add_done_callback(lambda f: subscription.dispose())

        return future

    def _remux_video(
        self, in_path: str, out_path: str, metadata_path: str
    ) -> Awaitable[RemuxingResult]:
        future: asyncio.Future[RemuxingResult] = asyncio.Future()
        self._postprocessing_path = in_path

        def on_next(value: Union[RemuxingProgress, RemuxingResult]) -> None:
            if isinstance(value, RemuxingProgress):
                self._postprocessing_progress = value
            elif isinstance(value, RemuxingResult):
                future.set_result(value)

        subscription = remux_video(
            in_path,
            out_path,
            metadata_path,
            display_progress=DISPLAY_PROGRESS,
            remove_filler_data=True,
        ).subscribe(
            on_next=on_next,
            on_error=lambda e: future.set_exception(e),
            scheduler=self._scheduler,
        )
        future.add_done_callback(lambda f: subscription.dispose())

        return future

    async def _is_vaild_flv_file(self, video_path: str) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, is_valid_flv_file, video_path)

    def _should_delete_source_files(self, remux_result: RemuxingResult) -> bool:
        if self.delete_source == DeleteStrategy.AUTO:
            if not remux_result.is_failed():
                return True
        elif self.delete_source == DeleteStrategy.SAFE:
            if not remux_result.is_failed() and not remux_result.is_warned():
                return True
        elif self.delete_source == DeleteStrategy.NEVER:
            return False

        return False

    async def _wait_for_metadata_file(self, video_path: str) -> None:
        _, ext = os.path.splitext(video_path)

        if ext == '.flv':
            path = extra_metadata_path(video_path)
        elif ext == '.m4s':
            path = record_metadata_path(video_path)
        else:
            return

        loop = asyncio.get_running_loop()

        for _ in range(10):
            if await loop.run_in_executor(None, os.path.isfile, path):
                break
            else:
                self._logger.debug(f'Not found metadata file: {path}')
                await asyncio.sleep(1)
        else:
            self._logger.warning(f'No such metadata file: {path}')
