import io
from typing import Callable, Optional

from loguru import logger
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from blrec.exception.helpers import format_exception

from ..common import create_avc_end_sequence_tag, is_avc_end_sequence
from ..io import FlvReader
from ..models import FlvTag
from .typing import FLVStream, FLVStreamItem

__all__ = ('parse',)


def parse(
    *,
    ignore_eof: bool = False,
    complete_on_eof: bool = False,
    ignore_value_error: bool = False,
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
                tag: Optional[FlvTag] = None
                try:
                    try:
                        reader = FlvReader(
                            stream,  # type: ignore
                            backup_timestamp=backup_timestamp,
                            restore_timestamp=restore_timestamp,
                        )
                        observer.on_next(reader.read_header())
                        while not disposed:
                            tag = reader.read_tag()
                            observer.on_next(tag)
                    finally:
                        if tag is not None and not is_avc_end_sequence(tag):
                            tag = create_avc_end_sequence_tag(
                                offset=tag.next_tag_offset, timestamp=tag.timestamp
                            )
                            observer.on_next(tag)
                        stream.close()
                except EOFError as e:
                    logger.debug(f'Error occurred while parsing stream: {repr(e)}')
                    if complete_on_eof:
                        observer.on_completed()
                    else:
                        if not ignore_eof:
                            observer.on_error(e)
                except ValueError as e:
                    logger.debug(
                        'Error occurred while parsing stream: {}\n{}',
                        repr(e),
                        format_exception(e),
                    )
                    if not ignore_value_error:
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
