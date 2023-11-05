from __future__ import annotations

import json
from contextlib import suppress
from typing import Any, Callable, Dict, Tuple

from loguru import logger

from blrec.path.helpers import record_metadata_path
from blrec.utils.mixins import SwitchableMixin

from . import operators as hls_ops

__all__ = ('MetadataDumper',)


class MetadataDumper(SwitchableMixin):
    def __init__(
        self,
        segment_dumper: hls_ops.SegmentDumper,
        metadata_provider: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        super().__init__()
        self._segment_dumper = segment_dumper
        self._metadata_provider = metadata_provider
        self._metadata: Dict[str, Any] = {}

    def _do_enable(self) -> None:
        self._file_opened_subscription = self._segment_dumper.file_opened.subscribe(
            self._on_video_file_opened
        )
        logger.debug('Enabled metadata dumper')

    def _do_disable(self) -> None:
        with suppress(Exception):
            self._file_opened_subscription.dispose()
            del self._file_opened_subscription
        self._metadata.clear()
        logger.debug('Disabled metadata dumper')

    def _on_video_file_opened(self, args: Tuple[str, int]) -> None:
        video_path, _timestamp = args
        metadata = self._metadata_provider({})
        self._dump_metadata(video_path, metadata)

    def _dump_metadata(self, video_path: str, metadata: Dict[str, Any]) -> None:
        path = record_metadata_path(video_path)
        logger.debug(f"Dumping metadata to file: '{path}'")

        with open(path, 'wt', encoding='utf8') as file:
            json.dump(metadata, file, ensure_ascii=False)
