from __future__ import annotations

from typing import Optional, Union

from loguru import logger
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from .playlist_dumper import PlaylistDumper
from .segment_dumper import SegmentDumper
from .segment_fetcher import InitSectionData, SegmentData

__all__ = ('Limiter',)


class Limiter:
    def __init__(
        self,
        playlist_dumper: PlaylistDumper,
        segment_dumper: SegmentDumper,
        *,
        filesize_limit: int = 0,  # file size in bytes, no limit by default.
        duration_limit: int = 0,  # duration in seconds, no limit by default.
    ) -> None:
        self._playlist_dumper = playlist_dumper
        self._segment_dumper = segment_dumper

        self.filesize_limit = filesize_limit
        self.duration_limit = duration_limit

    def _will_over_limits(self, item: Union[InitSectionData, SegmentData]) -> bool:
        if (
            self.filesize_limit > 0
            and self._segment_dumper.filesize + len(item) >= self.filesize_limit
        ):
            logger.debug(
                'File size will be over the limit: {} + {}'.format(
                    self._segment_dumper.filesize, len(item)
                )
            )
            return True

        if (
            self.duration_limit > 0
            and self._playlist_dumper.duration + float(item.segment.duration)
            >= self.duration_limit
        ):
            logger.debug(
                'Duration will be over the limit: {} + {}'.format(
                    self._playlist_dumper.duration, item.segment.duration
                )
            )
            return True

        return False

    def _add_flag(self, item: Union[InitSectionData, SegmentData]) -> None:
        item.segment.custom_parser_values['split'] = True

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._limit(source)

    def _limit(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        def subscribe(
            observer: abc.ObserverBase[Union[InitSectionData, SegmentData]],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            def on_next(item: Union[InitSectionData, SegmentData]) -> None:
                if self._will_over_limits(item):
                    self._add_flag(item)
                observer.on_next(item)

            def dispose() -> None:
                nonlocal disposed
                disposed = True

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
