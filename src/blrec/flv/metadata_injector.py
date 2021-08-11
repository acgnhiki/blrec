import os
import logging
from typing import Any, Dict, Optional

import attr
from rx import create, operators as op
from rx.subject import Subject
from rx.core import Observable
from rx.core.typing import Observer, Scheduler, Disposable
from rx.scheduler.currentthreadscheduler import CurrentThreadScheduler
from tqdm import tqdm

from .stream_processor import StreamProcessor, BaseOutputFileManager, JoinPoint
from .helpers import get_metadata, make_comment_for_joinpoints
from ..logging.room_id import with_room_id


__all__ = 'MetadataInjector', 'InjectProgress', 'inject_metadata'


logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class InjectProgress:
    time: int
    duration: int


class MetadataInjector:
    def __init__(self, in_path: str, out_path: str) -> None:
        self._in_path = in_path
        self._file_manager = OutputFileManager(out_path)
        self._duration: int = 0
        self._progress_updates = Subject()

    @property
    def progress_updates(self) -> Observable:
        return self._progress_updates

    def inject(self, in_metadata: Dict[str, Any]) -> None:
        metadata = get_metadata(self._in_path)
        metadata.update(in_metadata)

        self._duration = int(float(metadata['duration']) * 1000)
        self._progress_updates.on_next(InjectProgress(0, self._duration))

        self._append_comment_for_joinpoints(metadata)

        processor = StreamProcessor(
            self._file_manager,
            metadata=metadata,
            disable_limit=True,
        )

        def update_progress(time: int) -> None:
            progress = InjectProgress(time, self._duration)
            self._progress_updates.on_next(progress)

        processor.time_updates.subscribe(update_progress)

        with open(self._in_path, 'rb') as in_file:
            processor.process_stream(in_file)
            processor.finalize()

        progress = InjectProgress(self._duration, self._duration)
        self._progress_updates.on_next(progress)

    @staticmethod
    def _append_comment_for_joinpoints(metadata: Dict[str, Any]) -> None:
        if (join_points := metadata.get('joinpoints')):
            join_points = map(JoinPoint.from_metadata_value, join_points)
            if 'Comment' in metadata:
                metadata['Comment'] += '\n\n' + \
                    make_comment_for_joinpoints(join_points)
            else:
                metadata['Comment'] = make_comment_for_joinpoints(join_points)


class OutputFileManager(BaseOutputFileManager):
    def __init__(self, out_path: str) -> None:
        super().__init__()
        self._out_path = out_path

    def _make_path(self) -> str:
        return self._out_path


def inject_metadata(
    path: str,
    metadata: Dict[str, Any],
    *,
    report_progress: bool = False,
    room_id: Optional[int] = None,
) -> Observable:
    def subscribe(
        observer: Observer[InjectProgress],
        scheduler: Optional[Scheduler] = None,
    ) -> Disposable:
        _scheduler = scheduler or CurrentThreadScheduler.singleton()

        def action(scheduler, state):  # type: ignore
            root, ext = os.path.splitext(path)
            out_path = f'{root}_inject_metadata{ext}'
            injector = MetadataInjector(path, out_path)
            file_name = os.path.basename(path)

            with tqdm(desc='Injecting', unit='ms', postfix=file_name) as pbar:
                def reset(progress: InjectProgress) -> None:
                    pbar.reset(progress.duration)

                def update(progress: InjectProgress) -> None:
                    pbar.update(progress.time - pbar.n)

                injector.progress_updates.pipe(op.first()).subscribe(reset)
                injector.progress_updates.pipe(op.skip(1)).subscribe(update)

                if report_progress:
                    injector.progress_updates.subscribe(
                        lambda p: observer.on_next(p)
                    )

                try:
                    logger.info(f"Injecting metadata for '{path}' ...")
                    injector.inject(metadata)
                except Exception as e:
                    logger.error(
                        f"Failed to inject metadata for '{path}': {repr(e)}"
                    )
                    observer.on_error(e)
                else:
                    logger.info(f"Successfully inject metadata for '{path}'")
                    os.replace(out_path, path)
                    observer.on_completed()

        if room_id is not None:
            return _scheduler.schedule(with_room_id(room_id)(action))
        else:
            return _scheduler.schedule(action)

    return create(subscribe)
