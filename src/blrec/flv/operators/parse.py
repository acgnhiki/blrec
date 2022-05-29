import io
import logging
from typing import Callable, Optional

from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from ..io import FlvReader
from .typing import FLVStream, FLVStreamItem

__all__ = ('parse',)

logger = logging.getLogger(__name__)


def parse(
    *,
    ignore_eof: bool = False,
    complete_on_eof: bool = False,
    backup_timestamp: bool = False,
    restore_timestamp: bool = False,
) -> Callable[[Observable[io.RawIOBase]], FLVStream]:
    def _parse(source: Observable[io.RawIOBase]) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            def on_next(stream: io.RawIOBase) -> None:
                try:
                    try:
                        reader = FlvReader(
                            stream,
                            backup_timestamp=backup_timestamp,
                            restore_timestamp=restore_timestamp,
                        )
                        observer.on_next(reader.read_header())
                        while not disposed:
                            tag = reader.read_tag()
                            observer.on_next(tag)
                    finally:
                        stream.close()
                except EOFError as e:
                    if complete_on_eof:
                        observer.on_completed()
                    else:
                        if not ignore_eof:
                            observer.on_error(e)
                except Exception as e:
                    observer.on_error(e)
                else:
                    observer.on_completed()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            def dispose() -> None:
                nonlocal disposed
                disposed = True

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    return _parse
