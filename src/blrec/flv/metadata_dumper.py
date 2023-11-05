import json
from contextlib import suppress
from typing import List, Optional

import attr
from loguru import logger

from ..flv import operators as flv_ops
from ..path import extra_metadata_path
from ..utils.mixins import SwitchableMixin

__all__ = ('MetadataDumper',)


class MetadataDumper(SwitchableMixin):
    def __init__(
        self,
        dumper: flv_ops.Dumper,
        analyser: flv_ops.Analyser,
        joinpoint_extractor: flv_ops.JoinPointExtractor,
    ) -> None:
        super().__init__()
        self._dumper = dumper
        self._analyser = analyser
        self._joinpoint_extractor = joinpoint_extractor
        self._reset()

    def _reset(self) -> None:
        self._last_metadata: Optional[flv_ops.MetaData] = None
        self._last_join_points: Optional[List[flv_ops.JoinPoint]] = None

    def _do_enable(self) -> None:
        self._metadata_subscription = self._analyser.metadatas.subscribe(
            on_next=self._update_metadata
        )
        self._join_points_subscription = (
            self._joinpoint_extractor.join_points.subscribe(self._update_join_points)
        )
        self._file_closed_subscription = self._dumper.file_closed.subscribe(
            self._dump_metadata
        )
        self._reset()
        logger.debug('Enabled metadata dumper')

    def _do_disable(self) -> None:
        with suppress(Exception):
            self._metadata_subscription.dispose()
        with suppress(Exception):
            self._join_points_subscription.dispose()
        with suppress(Exception):
            self._file_closed_subscription.dispose()
        self._reset()
        logger.debug('Disabled metadata dumper')

    def _update_metadata(self, metadata: Optional[flv_ops.MetaData]) -> None:
        self._last_metadata = metadata

    def _update_join_points(self, join_points: List[flv_ops.JoinPoint]) -> None:
        self._last_join_points = join_points

    def _dump_metadata(self, video_path: str) -> None:
        path = extra_metadata_path(video_path)
        logger.debug(f"Dumping metadata to file: '{path}'")

        if self._last_metadata is not None:
            data = attr.asdict(self._last_metadata, filter=lambda a, v: v is not None)
        else:
            data = {}
            logger.warning('The metadata may be lost duo to something went wrong')

        if self._last_join_points is not None:
            data['joinpoints'] = list(
                map(lambda p: p.to_metadata_value(), self._last_join_points)
            )
        else:
            data['joinpoints'] = []
            logger.warning('The joinpoints may be lost duo to something went wrong')

        try:
            with open(path, 'wt', encoding='utf8') as file:
                json.dump(data, file)
        except Exception as e:
            logger.error(f'Failed to dump metadata: {e}')
        else:
            logger.debug(f"Successfully dumped metadata to file: '{path}'")
