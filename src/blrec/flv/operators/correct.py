from typing import Callable, Optional

from loguru import logger
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from ..common import is_script_tag, is_sequence_header
from ..models import FlvHeader, FlvTag
from .typing import FLVStream, FLVStreamItem

__all__ = ('correct',)


def correct() -> Callable[[FLVStream], FLVStream]:
    def _correct(source: FLVStream) -> FLVStream:
        """Correct the timestamp offset of the FLV tags."""

        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            delta: Optional[int] = None
            first_data_tag: Optional[FlvTag] = None

            def reset() -> None:
                nonlocal delta, first_data_tag
                delta = None
                first_data_tag = None

            def correct_ts(tag: FlvTag, delta: int) -> FlvTag:
                if delta == 0:
                    return tag
                return tag.evolve(timestamp=tag.timestamp + delta)

            def on_next(item: FLVStreamItem) -> None:
                nonlocal delta
                nonlocal first_data_tag

                if isinstance(item, FlvHeader):
                    delta = None
                    first_data_tag = None
                    observer.on_next(item)
                    return

                tag = item

                if is_script_tag(tag):
                    tag = correct_ts(tag, -tag.timestamp)
                    observer.on_next(tag)
                    return

                if delta is None:
                    if is_sequence_header(tag):
                        tag = correct_ts(tag, -tag.timestamp)
                        observer.on_next(tag)
                    else:
                        if first_data_tag is None:
                            first_data_tag = tag
                            logger.debug(f'The first data tag: {first_data_tag}')
                        else:
                            second_data_tag = tag
                            logger.debug(f'The second data tag: {second_data_tag}')
                            if second_data_tag.timestamp >= first_data_tag.timestamp:
                                delta = -first_data_tag.timestamp
                                logger.debug(f'Timestamp delta: {delta}')
                                observer.on_next(correct_ts(first_data_tag, delta))
                                observer.on_next(correct_ts(second_data_tag, delta))
                            else:
                                delta = -second_data_tag.timestamp
                                logger.debug(f'Timestamp delta: {delta}')
                                observer.on_next(correct_ts(second_data_tag, delta))
                                observer.on_next(correct_ts(first_data_tag, delta))
                            first_data_tag = None
                    return

                tag = correct_ts(tag, delta)
                observer.on_next(tag)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                reset()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    return _correct
