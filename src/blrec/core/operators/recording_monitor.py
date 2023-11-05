from __future__ import annotations

import time
from typing import Callable, Final, Optional, Tuple, TypeVar

from reactivex import Observable, Subject, abc

from blrec.bili.live import Live
from blrec.utils.mixins import AsyncCooperationMixin

__all__ = ('RecordingMonitor',)


_T = TypeVar('_T')


class RecordingMonitor(AsyncCooperationMixin):
    def __init__(
        self,
        live: Live,
        duration_provider: Callable[..., float],
        duration_updated: Observable[float],
    ) -> None:
        super().__init__()
        self._live = live
        self._duration_provider = duration_provider
        self._duration_updated = duration_updated
        self._duration_subscription: Optional[abc.DisposableBase] = None
        self._interrupted: Subject[Tuple[float, float]] = Subject()
        self._recovered: Subject[float] = Subject()

    @property
    def interrupted(self) -> Observable[Tuple[float, float]]:
        return self._interrupted

    @property
    def recovered(self) -> Observable[float]:
        return self._recovered

    def _on_duration_updated(self, duration: float) -> None:
        ts = time.time()
        self._recovered.on_next(ts)
        assert self._duration_subscription is not None
        self._duration_subscription.dispose()
        self._duration_subscription = None

    def __call__(self, source: Observable[_T]) -> Observable[_T]:
        return self._monitor(source)

    def _monitor(self, source: Observable[_T]) -> Observable[_T]:
        CRITERIA: Final[int] = 1
        recording: bool = False
        failed_count: int = 0

        def subscribe(
            observer: abc.ObserverBase[_T],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            def on_next(item: _T) -> None:
                nonlocal recording, failed_count
                recording = True
                if failed_count >= CRITERIA:
                    if self._duration_subscription is not None:
                        self._duration_subscription.dispose()
                    self._duration_subscription = self._duration_updated.subscribe(
                        self._on_duration_updated
                    )
                failed_count = 0
                observer.on_next(item)

            def on_error(exc: Exception) -> None:
                nonlocal failed_count
                if recording:
                    failed_count += 1
                    if failed_count == CRITERIA:
                        ts = time.time()
                        duration = self._duration_provider()
                        self._interrupted.on_next((ts, duration))
                observer.on_error(exc)

            return source.subscribe(
                on_next, on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)
