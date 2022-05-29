import logging
import os
from datetime import datetime
from typing import Any, Dict

import attr
from reactivex import Observable
from reactivex import operators as ops

from ..utils import operators as utils_ops
from . import operators as flv_ops
from .helpers import make_comment_for_joinpoints
from .operators import JoinPoint
from .operators.helpers import from_file

__all__ = 'InjectingProgress', 'inject_metadata'


logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class InjectingProgress:
    count: int
    total: int


def inject_metadata(
    path: str, metadata: Dict[str, Any], *, show_progress: bool = False
) -> Observable[InjectingProgress]:
    filesize = os.path.getsize(path)
    append_comment_for_joinpoints(metadata)

    root, ext = os.path.splitext(path)
    temp_path = f'{root}_injecting{ext}'
    filename = os.path.basename(path)

    return from_file(path).pipe(
        flv_ops.Injector(lambda: metadata),
        flv_ops.Dumper(lambda: (temp_path, int(datetime.now().timestamp()))),
        flv_ops.ProgressBar(
            desc='Injecting',
            postfix=filename,
            total=filesize,
            disable=not show_progress,
        ),
        ops.map(lambda i: len(i)),
        ops.scan(lambda acc, x: acc + x, 0),
        ops.map(lambda s: InjectingProgress(s, filesize)),
        utils_ops.replace(temp_path, path),
    )


def append_comment_for_joinpoints(metadata: Dict[str, Any]) -> None:
    if join_points := metadata.get('joinpoints'):
        join_points = map(JoinPoint.from_metadata_value, join_points)
        if 'Comment' in metadata:
            metadata['Comment'] += '\n\n' + make_comment_for_joinpoints(join_points)
        else:
            metadata['Comment'] = make_comment_for_joinpoints(join_points)
