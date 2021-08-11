import asyncio
import logging
from pathlib import PurePath
from typing import (
    Any, Awaitable, Dict, Iterable, Iterator, List, Optional, Sequence, Set,
    Tuple, Union,
)

from rx.core.typing import Scheduler
from rx.scheduler.threadpoolscheduler import ThreadPoolScheduler

from .models import ProcessStatus, DeleteStrategy
from .typing import Progress
from .remuxer import remux_video, RemuxProgress, RemuxResult
from .helpers import discard_file, discard_files, get_extra_metadata
from .ffmpeg_metadata import make_metadata_file
from ..event.event_emitter import EventListener, EventEmitter
from ..bili.live import Live
from ..core import Recorder, RecorderEventListener
from ..exception import exception_callback
from ..utils.mixins import SwitchableMixin, AsyncCooperationMix
from ..path import danmaku_path, extra_metadata_path
from ..flv.metadata_injector import inject_metadata, InjectProgress
from ..flv.helpers import is_valid
from ..logging.room_id import aio_task_with_room_id


__all__ = (
    'Postprocessor',
    'PostprocessorEventListener',
    'ProcessStatus',
    'DeleteStrategy',
)


logger = logging.getLogger(__name__)


class PostprocessorEventListener(EventListener):
    async def on_file_completed(self, room_id: int, path: str) -> None:
        ...


class Postprocessor(
    EventEmitter[PostprocessorEventListener],
    RecorderEventListener,
    SwitchableMixin,
    AsyncCooperationMix,
):
    def __init__(
        self,
        live: Live,
        recorder: Recorder,
        *,
        remux_to_mp4: bool = False,
        delete_source: DeleteStrategy = DeleteStrategy.AUTO,
    ) -> None:
        super().__init__()

        self._live = live
        self._recorder = recorder

        self.remux_to_mp4 = remux_to_mp4
        self.delete_source = delete_source

        self._status = ProcessStatus.WAITING
        self._postprocessing_path: Optional[str] = None
        self._postprocessing_progress: Optional[Progress] = None
        self._files: List[str] = []

    @property
    def status(self) -> ProcessStatus:
        return self._status

    @property
    def postprocessing_path(self) -> Optional[str]:
        return self._postprocessing_path

    @property
    def postprocessing_progress(self) -> Optional[Progress]:
        return self._postprocessing_progress

    def get_final_files(self) -> Iterator[str]:
        yield from iter(self._files)

    async def wait(self) -> None:
        await self._wait_processing_task()

    async def on_recording_finished(self, recorder: Recorder) -> None:
        self._create_processing_task(recorder)

    async def on_recording_cancelled(self, recorder: Recorder) -> None:
        self._create_processing_task(recorder)

    def _do_enable(self) -> None:
        self._recorder.add_listener(self)
        logger.debug('Enabled postprocessor')

    def _do_disable(self) -> None:
        self._recorder.remove_listener(self)
        logger.debug('Disabled postprocessor')

    def _create_processing_task(self, recorder: Recorder) -> None:
        raw_videos = list(recorder.get_video_files())
        raw_danmaku = list(recorder.get_danmaku_files())
        self._processing_task = asyncio.create_task(
            self._process(raw_videos, raw_danmaku),
        )
        self._processing_task.add_done_callback(exception_callback)

    async def _wait_processing_task(self) -> None:
        if hasattr(self, '_processing_task'):
            await self._processing_task

    @aio_task_with_room_id
    async def _process(
        self, raw_videos: Sequence[str], raw_danmaku: Sequence[str]
    ) -> None:
        raw_videos, raw_danmaku = await self._discard_invaild_files(
            raw_videos, raw_danmaku
        )

        self._files.clear()

        if self.remux_to_mp4:
            self._status = ProcessStatus.REMUXING
            final_videos = await self._remux_videos(raw_videos)
        else:
            self._status = ProcessStatus.INJECTING
            await self._inject_extra_metadata(raw_videos)
            final_videos = raw_danmaku

        self._files.extend(final_videos)
        self._files.extend(raw_danmaku)

        self._status = ProcessStatus.WAITING
        self._postprocessing_path = None
        self._postprocessing_progress = None

    async def _discard_invaild_files(
        self, raw_videos: Sequence[str], raw_danmaku: Sequence[str]
    ) -> Tuple[List[str], List[str]]:
        loop = asyncio.get_running_loop()
        valid_video_set: Set[str] = await loop.run_in_executor(
            None, set, filter(is_valid, raw_videos)
        )
        invalid_video_set = set(raw_videos) - valid_video_set

        if invalid_video_set:
            logger.info('Discarding invalid files ...')
            await discard_files(invalid_video_set)
            await discard_files(map(danmaku_path, invalid_video_set))

        return list(valid_video_set), list(map(danmaku_path, valid_video_set))

    async def _inject_extra_metadata(self, video_paths: Iterable[str]) -> None:
        scheduler = ThreadPoolScheduler()
        for path in video_paths:
            metadata = await get_extra_metadata(path)
            await self._inject_metadata(path, metadata, scheduler)
            await discard_file(extra_metadata_path(path), 'DEBUG')
            await self._emit('file_completed', self._live.room_id, path)

    async def _remux_videos(self, video_paths: Iterable[str]) -> List[str]:
        results = []
        scheduler = ThreadPoolScheduler()

        for in_path in video_paths:
            out_path = str(PurePath(in_path).with_suffix('.mp4'))
            logger.info(f"Remuxing '{in_path}' to '{out_path}' ...")

            metadata_path = await make_metadata_file(in_path)
            remux_result = await self._remux_video(
                in_path, out_path, metadata_path, scheduler
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

            if self._should_delete_source_files(remux_result):
                await discard_file(in_path)
                await discard_files(
                    [metadata_path, extra_metadata_path(in_path)], 'DEBUG'
                )

            results.append(result_path)
            await self._emit('file_completed', self._live.room_id, result_path)

        return results

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

    def _should_delete_source_files(
        self, remux_result: RemuxResult
    ) -> bool:
        if self.delete_source == DeleteStrategy.AUTO:
            if not remux_result.is_failed():
                return True
        elif self.delete_source == DeleteStrategy.NEVER:
            return False

        return False
