import logging
import os
from typing import Optional, Tuple, Union

from reactivex import Observable, Subject, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from blrec.hls.operators.segment_fetcher import InitSectionData, SegmentData

from .playlist_dumper import PlaylistDumper

__all__ = ('SegmentDumper',)

logger = logging.getLogger(__name__)


class SegmentDumper:
    def __init__(self, playlist_dumper: PlaylistDumper) -> None:
        self._playlist_dumper = playlist_dumper
        self._out_dir: str = ''

        def on_next(args: Tuple[str, int]) -> None:
            path, timestamp = args
            self._out_dir = os.path.dirname(path)

        self._playlist_dumper.file_opened.subscribe(on_next)
        self._file_opened: Subject[Tuple[str, int]] = Subject()
        self._file_closed: Subject[str] = Subject()

    @property
    def file_opened(self) -> Observable[Tuple[str, int]]:
        return self._file_opened

    @property
    def file_closed(self) -> Observable[str]:
        return self._file_closed

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._dump(source)

    def _dump(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        def subscribe(
            observer: abc.ObserverBase[Union[InitSectionData, SegmentData]],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            subscription = SerialDisposable()

            def on_next(item: Union[InitSectionData, SegmentData]) -> None:
                if isinstance(item, InitSectionData):
                    uri = item.init_section.uri
                    path = os.path.join(self._out_dir, 'segments', uri)
                else:
                    uri = item.segment.uri
                    name, ext = os.path.splitext(uri)
                    path = os.path.join(self._out_dir, 'segments', name[:-3], uri)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                try:
                    with open(path, 'wb') as file:
                        file.write(item.payload)
                except Exception as e:
                    logger.error(f'Failed to dump segmemt: {repr(e)}')
                    observer.on_error(e)
                else:
                    observer.on_next(item)

            def dispose() -> None:
                pass

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
