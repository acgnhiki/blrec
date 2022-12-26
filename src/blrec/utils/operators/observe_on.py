from queue import Queue
from threading import Thread
from typing import Any, Callable, Optional, TypeVar

from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable


_T = TypeVar('_T')


def observe_on_new_thread(
    queue_size: Optional[int] = None, thread_name: Optional[str] = None
) -> Callable[[Observable[_T]], Observable[_T]]:
    def observe_on(source: Observable[_T]) -> Observable[_T]:
        def subscribe(
            observer: abc.ObserverBase[_T],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()
            queue: Queue[Callable[..., Any]] = Queue(maxsize=queue_size or 0)

            def run() -> None:
                while not disposed:
                    queue.get()()

            thread = Thread(target=run, name=thread_name, daemon=True)
            thread.start()

            def on_next(value: _T) -> None:
                queue.put(lambda: observer.on_next(value))

            def on_error(exc: Exception) -> None:
                queue.put(lambda: observer.on_error(exc))

            def on_completed() -> None:
                queue.put(lambda: observer.on_completed)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                queue.put(lambda: None)
                thread.join()

            subscription.disposable = source.subscribe(
                on_next, on_error, on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    return observe_on
