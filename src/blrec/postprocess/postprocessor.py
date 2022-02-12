from __future__ import annotations
import asyncio
import logging
from pathlib import PurePath
from contextlib import suppress
from typing import Any, Awaitable, Dict, Iterator, List, Optional, Union

from rx.core.typing import Scheduler
from rx.scheduler.threadpoolscheduler import ThreadPoolScheduler

from .models import PostprocessorStatus, DeleteStrategy
from .typing import Progress
from .remuxer import remux_video, RemuxProgress, RemuxResult
from .helpers import discard_file, get_extra_metadata
from .ffmpeg_metadata import make_metadata_file
from ..event.event_emitter import EventListener, EventEmitter
from ..bili.live import Live
from ..core import Recorder, RecorderEventListener
from ..exception import submit_exception
from ..utils.mixins import AsyncStoppableMixin, AsyncCooperationMix
from ..path import extra_metadata_path
from ..flv.metadata_injector import inject_metadata, InjectProgress
from ..flv.helpers import is_valid_flv_file
from ..logging.room_id import aio_task_with_room_id


__all__ = (
    'Postprocessor',
    'PostprocessorEventListener',
    'PostprocessorStatus',
    'DeleteStrategy',
)


logger = logging.getLogger(__name__)


class PostprocessorEventListener(EventListener):
    async def on_video_postprocessing_completed(
        self, postprocessor: Postprocessor, path: str
    ) -> None:
        ...


class Postprocessor(
    EventEmitter[PostprocessorEventListener],
    RecorderEventListener,
    AsyncStoppableMixin,
    AsyncCooperationMix,
):
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

    async def on_video_file_completed(
        self, recorder: Recorder, path: str
    ) -> None:
        self._queue.put_nowait(path)

    async def on_danmaku_file_completed(
        self, recorder: Recorder, path: str
    ) -> None:
        self._completed_files.append(path)

    async def _do_start(self) -> None:
        self._recorder.add_listener(self)

        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._scheduler = ThreadPoolScheduler()
        self._task = asyncio.create_task(self._worker())

        logger.debug('Started postprocessor')

    async def _do_stop(self) -> None:
        self._recorder.remove_listener(self)

        await self._queue.join()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task

        del self._queue
        del self._scheduler
        del self._task

        logger.debug('Stopped postprocessor')

    @aio_task_with_room_id
    async def _worker(self) -> None:
        while True:
            self._status = PostprocessorStatus.WAITING
            self._postprocessing_path = None
            self._postprocessing_progress = None

            video_path = await self._queue.get()

            if not await self._is_vaild_flv_file(video_path):
                self._queue.task_done()
                continue

            try:
                if self.remux_to_mp4:
                    self._status = PostprocessorStatus.REMUXING
                    result_path = await self._remux_flv_to_mp4(video_path)
                elif self.inject_extra_metadata:
                    self._status = PostprocessorStatus.INJECTING
                    result_path = await self._inject_extra_metadata(video_path)
                else:
                    result_path = video_path

                await discard_file(extra_metadata_path(video_path), 'DEBUG')

                self._completed_files.append(result_path)
                await self._emit(
                    'video_postprocessing_completed', self, result_path,
                )
            except Exception as exc:
                submit_exception(exc)
            finally:
                self._queue.task_done()

    async def _inject_extra_metadata(self, path: str) -> str:
        metadata = await get_extra_metadata(path)
        await self._inject_metadata(path, metadata, self._scheduler)
        return path

    async def _remux_flv_to_mp4(self, in_path: str) -> str:
        out_path = str(PurePath(in_path).with_suffix('.mp4'))
        logger.info(f"Remuxing '{in_path}' to '{out_path}' ...")

        metadata_path = await make_metadata_file(in_path)
        remux_result = await self._remux_video(
            in_path, out_path, metadata_path, self._scheduler
        )

        if remux_result.is_successful():
            logger.info(f"Successfully remux '{in_path}' to '{out_path}'")
            result_path = out_path
        elif remux_result.is_warned():
            logger.warning('Remuxing done, but ran into problems.')
            result_path = out_path
        elif remux_result.is_failed:
            logger.error(f"Failed to remux '{in_path}' to '{out_path}'")
            result_path = in_path
        else:
            pass

        logger.debug(f'ffmpeg output:\n{remux_result.output}')

        await discard_file(metadata_path, 'DEBUG')
        if self._should_delete_source_files(remux_result):
            await discard_file(in_path)

        return result_path

    def _inject_metadata(
        self,
        path: str,
        metadata: Dict[str, Any],
        scheduler: Scheduler,
    ) -> Awaitable[None]:
        future: asyncio.Future[None] = asyncio.Future()
        self._postprocessing_path = path

        def on_next(value: InjectProgress) -> None:
            self._postprocessing_progress = value

        inject_metadata(
            path,
            metadata,
            report_progress=True,
            room_id=self._live.room_id,
        ).subscribe(
            on_next,
            lambda e: future.set_exception(e),
            lambda: future.set_result(None),
            scheduler=scheduler,
        )

        return future

    def _remux_video(
        self,
        in_path: str,
        out_path: str,
        metadata_path: str,
        scheduler: Scheduler,
    ) -> Awaitable[RemuxResult]:
        future: asyncio.Future[RemuxResult] = asyncio.Future()
        self._postprocessing_path = in_path

        def on_next(value: Union[RemuxProgress, RemuxResult]) -> None:
            if isinstance(value, RemuxProgress):
                self._postprocessing_progress = value
            elif isinstance(value, RemuxResult):
                future.set_result(value)

        remux_video(
            in_path,
            out_path,
            metadata_path,
            report_progress=True,
        ).subscribe(
            on_next,
            lambda e: future.set_exception(e),
            scheduler=scheduler,
        )

        return future

    async def _is_vaild_flv_file(self, video_path: str) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, is_valid_flv_file, video_path)

    def _should_delete_source_files(
        self, remux_result: RemuxResult
    ) -> bool:
        if self.delete_source == DeleteStrategy.AUTO:
            if not remux_result.is_failed():
                return True
        elif self.delete_source == DeleteStrategy.NEVER:
            return False

        return False
