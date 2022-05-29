import os
from typing import Callable, Optional, TypeVar

from reactivex import Observable, abc

_T = TypeVar('_T')


def replace(src_path: str, dst_path: str) -> Callable[[Observable[_T]], Observable[_T]]:
    def _replace(source: Observable[_T]) -> Observable[_T]:
        def subscribe(
            observer: abc.ObserverBase[_T],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            def on_completed() -> None:
                try:
                    os.replace(src_path, dst_path)
                except Exception as e:
                    observer.on_error(e)
                else:
                    observer.on_completed()

            return source.subscribe(
                observer.on_next, observer.on_error, on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    return _replace
