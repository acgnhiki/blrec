from __future__ import annotations

from typing import Optional, Tuple, Union

from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from .playlist_dumper import PlaylistDumper
from .segment_fetcher import InitSectionData, SegmentData

__all__ = ('Cutter',)


class Cutter:
    def __init__(
        self, playlist_dumper: PlaylistDumper, min_duration: float = 5.0
    ) -> None:
        self._playlist_dumper = playlist_dumper
        self._min_duration = min_duration  # seconds

        self._cutting: bool
        self._triggered: bool
        self._reset()

        def on_open(args: Tuple[str, int]) -> None:
            self._cutting = False

        self._playlist_dumper.file_opened.subscribe(on_open)

    def _reset(self) -> None:
        self._cutting = False
        self._triggered = False

    def is_cutting(self) -> bool:
        return self._cutting

    def can_cut_stream(self) -> bool:
        if self._triggered or self._cutting:
            return False
        return self._playlist_dumper.duration >= self._min_duration

    def cut_stream(self) -> bool:
        if self.can_cut_stream():
            self._triggered = True
            return True
        return False

    def _add_flag(self, item: Union[InitSectionData, SegmentData]) -> None:
        item.segment.custom_parser_values['split'] = True

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._cut(source)

    def _cut(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        def subscribe(
            observer: abc.ObserverBase[Union[InitSectionData, SegmentData]],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            self._reset()

            def on_next(item: Union[InitSectionData, SegmentData]) -> None:
                if self._triggered:
                    self._add_flag(item)
                    self._cutting = True
                    self._triggered = False

                observer.on_next(item)

            def dispose() -> None:
                nonlocal disposed
                disposed = True

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
