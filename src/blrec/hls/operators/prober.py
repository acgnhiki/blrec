from __future__ import annotations

import io
from typing import List, Optional, Union

from loguru import logger
from reactivex import Observable, Subject, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from blrec.utils.ffprobe import StreamProfile, ffprobe_on

from .segment_fetcher import InitSectionData, SegmentData

__all__ = ('Prober', 'StreamProfile')


class Prober:
    def __init__(self) -> None:
        self._profiles: Subject[StreamProfile] = Subject()

    def _reset(self) -> None:
        self._gathering: bool = False
        self._gathered_items: List[Union[InitSectionData, SegmentData]] = []

    @property
    def profiles(self) -> Observable[StreamProfile]:
        return self._profiles

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._probe(source)

    def _probe(
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
                if isinstance(item, InitSectionData):
                    self._gathered_items.clear()
                    self._gathering = True

                if self._gathering:
                    self._gathered_items.append(item)
                    if len(self._gathered_items) >= 10:
                        try:
                            self._do_probe()
                        except Exception as e:
                            logger.warning(f'Failed to probe stream: {repr(e)}')
                        finally:
                            self._gathered_items.clear()
                            self._gathering = False

                observer.on_next(item)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                self._reset()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    def _do_probe(self) -> None:
        bytes_io = io.BytesIO()
        for item in self._gathered_items:
            bytes_io.write(item.payload)

        def on_next(profile: StreamProfile) -> None:
            self._profiles.on_next(profile)

        def on_error(e: Exception) -> None:
            logger.warning(f'Failed to probe stream by ffprobe: {repr(e)}')

        ffprobe_on(bytes_io.getvalue()).subscribe(on_next, on_error)
