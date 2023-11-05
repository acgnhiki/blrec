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


@attr.s(auto_attribs=True, slots=True, frozen=True)
class InjectingProgress:
    count: int
    total: int


def inject_metadata(
    path: str, metadata: Dict[str, Any], *, display_progress: bool = False
) -> Observable[InjectingProgress]:
    filesize = os.path.getsize(path)

    root, ext = os.path.splitext(path)
    temp_path = f'{root}_injecting{ext}'
    filename = os.path.basename(path)

    def metadata_provider(original_metadata: Dict[str, Any]) -> Dict[str, Any]:
        if joinpoints := metadata.get('joinpoints'):
            join_points = map(JoinPoint.from_metadata_value, joinpoints)
            if comment := original_metadata.get('Comment'):
                comment += '\n' + make_comment_for_joinpoints(join_points)
            else:
                comment = make_comment_for_joinpoints(join_points)
            metadata['Comment'] = comment
        return metadata

    return from_file(path).pipe(
        flv_ops.Injector(metadata_provider),
        flv_ops.Dumper(lambda: (temp_path, int(datetime.now().timestamp()))),
        flv_ops.ProgressBar(
            desc='Injecting',
            postfix=filename,
            total=filesize,
            disable=not display_progress,
        ),
        ops.map(lambda i: len(i)),  # type: ignore
        ops.scan(lambda acc, x: acc + x, 0),  # type: ignore
        ops.map(lambda s: InjectingProgress(s, filesize)),  # type: ignore
        utils_ops.replace(temp_path, path),
    )
