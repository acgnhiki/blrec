import logging
from typing import Callable

from .concat import concat
from .defragment import defragment
from .fix import fix
from .split import split
from .typing import FLVStream

__all__ = ('process',)

logger = logging.getLogger(__name__)


def process() -> Callable[[FLVStream], FLVStream]:
    def _process(source: FLVStream) -> FLVStream:
        return source.pipe(defragment(), split(), fix(), concat())

    return _process
