from __future__ import annotations

import json
import logging
from contextlib import suppress
from typing import Any, Callable, Dict, Tuple

from blrec.path.helpers import record_metadata_path
from blrec.utils.mixins import SwitchableMixin

from . import operators as hls_ops

__all__ = ('MetadataDumper',)

logger = logging.getLogger(__name__)


class MetadataDumper(SwitchableMixin):
    def __init__(
        self,
        playlist_dumper: hls_ops.PlaylistDumper,
        metadata_provider: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        super().__init__()
        self._playlist_dumper = playlist_dumper
        self._metadata_provider = metadata_provider
        self._metadata: Dict[str, Any] = {}

    def _do_enable(self) -> None:
        self._file_opened_subscription = self._playlist_dumper.file_opened.subscribe(
            self._on_playlist_file_opened
        )
        logger.debug('Enabled metadata dumper')

    def _do_disable(self) -> None:
        with suppress(Exception):
            self._file_opened_subscription.dispose()
            del self._file_opened_subscription
        self._metadata.clear()
        logger.debug('Disabled metadata dumper')

    def _on_playlist_file_opened(self, args: Tuple[str, int]) -> None:
        playlist_path, _ = args
        metadata = self._metadata_provider({})
        self._dump_metadata(playlist_path, metadata)

    def _dump_metadata(self, playlist_path: str, metadata: Dict[str, Any]) -> None:
        path = record_metadata_path(playlist_path)
        logger.debug(f"Dumping metadata to file: '{path}'")

        with open(path, 'wt', encoding='utf8') as file:
            json.dump(metadata, file, ensure_ascii=False)
