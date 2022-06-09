from __future__ import annotations

from typing import Optional, Sized

from reactivex import Observable, abc

from ..statistics import Statistics

__all__ = ('SizedStatistics',)


class SizedStatistics:
    def __init__(self) -> None:
        self._statistics = Statistics()

    @property
    def count(self) -> int:
        return self._statistics.count

    @property
    def rate(self) -> float:
        return self._statistics.rate

    @property
    def elapsed(self) -> float:
        return self._statistics.elapsed

    def freeze(self) -> None:
        self._statistics.freeze()

    def reset(self) -> None:
        self._statistics.reset()

    def __call__(self, source: Observable[Sized]) -> Observable[Sized]:
        self.reset()
        return self._calc(source)

    def _calc(self, source: Observable[Sized]) -> Observable[Sized]:
        def subscribe(
            observer: abc.ObserverBase[Sized],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            def on_next(item: Sized) -> None:
                self._statistics.submit(len(item))
                observer.on_next(item)

            def on_completed() -> None:
                self._statistics.freeze()
                observer.on_completed()

            return source.subscribe(
                on_next, observer.on_error, on_completed, scheduler=scheduler
            )

        return Observable(subscribe)
