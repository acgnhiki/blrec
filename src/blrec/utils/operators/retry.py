import time
from typing import Callable, Iterator, Optional, TypeVar

from reactivex import Observable, abc, catch_with_iterable
from reactivex import operators as ops

_T = TypeVar('_T')


def retry(
    count: Optional[int] = None,
    delay: Optional[float] = None,
    should_retry: Callable[[Exception], bool] = lambda _: True,
) -> Callable[[Observable[_T]], Observable[_T]]:
    def _retry(source: Observable[_T]) -> Observable[_T]:
        def subscribe(
            observer: abc.ObserverBase[_T],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            exception: Optional[Exception] = None

            def counter() -> Iterator[int]:
                n = 0
                while True:
                    if exception is not None:
                        if not should_retry(exception):
                            break
                        if count is not None and n > count:
                            break
                        if delay:
                            time.sleep(delay)
                    yield n
                    n += 1

            def on_error(e: Exception) -> None:
                nonlocal exception
                exception = e

            _source = source.pipe(ops.do_action(on_error=on_error))
            return catch_with_iterable(_source for _ in counter()).subscribe(
                observer, scheduler=scheduler
            )

        return Observable(subscribe)

    return _retry
