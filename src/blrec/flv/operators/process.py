import logging
from typing import Callable

from reactivex import operators as ops

from ..common import is_avc_end_sequence_tag
from .concat import concat
from .defragment import defragment
from .fix import fix
from .sort import sort
from .split import split
from .typing import FLVStream

__all__ = ('process',)

logger = logging.getLogger(__name__)


def process(
    sort_tags: bool = False, trace: bool = False
) -> Callable[[FLVStream], FLVStream]:
    def _process(source: FLVStream) -> FLVStream:
        if sort_tags:
            return source.pipe(
                defragment(),
                sort(trace=trace),
                ops.filter(lambda v: not is_avc_end_sequence_tag(v)),  # type: ignore
                split(),
                fix(),
                concat(),
            )
        else:
            return source.pipe(
                defragment(),
                ops.filter(lambda v: not is_avc_end_sequence_tag(v)),  # type: ignore
                split(),
                fix(),
                concat(),
            )

    return _process
