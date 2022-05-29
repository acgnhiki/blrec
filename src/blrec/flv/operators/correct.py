import logging
from typing import Callable, Optional

from reactivex import Observable, abc

from ..common import is_script_tag, is_sequence_header
from ..models import FlvHeader, FlvTag
from .typing import FLVStream, FLVStreamItem

__all__ = ('correct',)

logger = logging.getLogger(__name__)


def correct() -> Callable[[FLVStream], FLVStream]:
    def _correct(source: FLVStream) -> FLVStream:
        """Correct the timestamp offset of the FLV tags."""

        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            delta: Optional[int] = None

            def correct_ts(tag: FlvTag, delta: int) -> FlvTag:
                if delta == 0:
                    return tag
                return tag.evolve(timestamp=tag.timestamp + delta)

            def on_next(item: FLVStreamItem) -> None:
                nonlocal delta

                if isinstance(item, FlvHeader):
                    delta = None
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
                    else:
                        logger.debug(f'The first data tag: {tag}')
                        delta = -tag.timestamp
                        logger.debug(f'Timestamp delta: {delta}')
                        tag = correct_ts(tag, delta)
                else:
                    tag = correct_ts(tag, delta)

                observer.on_next(tag)

            return source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    return _correct
