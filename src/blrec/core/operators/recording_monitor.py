from __future__ import annotations

import logging
from typing import Callable, Final, Optional, TypeVar

from reactivex import Observable, Subject, abc

from blrec.bili.live import Live
from blrec.utils.mixins import AsyncCooperationMixin

__all__ = ('RecordingMonitor',)


logger = logging.getLogger(__name__)

_T = TypeVar('_T')


class RecordingMonitor(AsyncCooperationMixin):
    def __init__(self, live: Live, duration_provider: Callable[..., float]) -> None:
        super().__init__()
        self._live = live
        self._duration_provider = duration_provider
        self._interrupted: Subject[float] = Subject()
        self._recovered: Subject[int] = Subject()

    @property
    def interrupted(self) -> Observable[float]:
        return self._interrupted

    @property
    def recovered(self) -> Observable[int]:
        return self._recovered

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
                    ts = self._run_coroutine(self._live.get_timestamp())
                    self._recovered.on_next(ts)
                failed_count = 0
                observer.on_next(item)

            def on_error(exc: Exception) -> None:
                nonlocal failed_count
                if recording:
                    failed_count += 1
                    if failed_count == CRITERIA:
                        duration = self._duration_provider()
                        self._interrupted.on_next(duration)
                observer.on_error(exc)

            return source.subscribe(
                on_next, on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)
