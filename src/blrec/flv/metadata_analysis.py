import json
import os

import attr
from loguru import logger
from reactivex import Observable
from reactivex import operators as ops

from ..path import extra_metadata_path
from . import operators as flv_ops
from .operators.helpers import from_file

__all__ = 'AnalysingProgress', 'analyse_metadata'


@attr.s(auto_attribs=True, slots=True, frozen=True)
class AnalysingProgress:
    count: int
    total: int


def analyse_metadata(
    path: str, *, display_progress: bool = False
) -> Observable[AnalysingProgress]:
    filesize = os.path.getsize(path)
    filename = os.path.basename(path)

    def dump_metadata() -> None:
        try:
            metadata = analyser.make_metadata()
            data = attr.asdict(metadata, filter=lambda a, v: v is not None)
            file_path = extra_metadata_path(path)
            with open(file_path, 'wt', encoding='utf8') as file:
                json.dump(data, file)
        except Exception as e:
            logger.error(f'Failed to dump metadata: {e}')
        else:
            logger.debug(f"Successfully dumped metadata to file: '{path}'")

    analyser = flv_ops.Analyser()
    return from_file(path).pipe(
        analyser,
        flv_ops.ProgressBar(
            desc='Analysing',
            postfix=filename,
            total=filesize,
            disable=not display_progress,
        ),
        ops.map(lambda i: len(i)),  # type: ignore
        ops.scan(lambda acc, x: acc + x, 0),  # type: ignore
        ops.map(lambda s: AnalysingProgress(s, filesize)),  # type: ignore
        ops.do_action(on_completed=dump_metadata),
    )
