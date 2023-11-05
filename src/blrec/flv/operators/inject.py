from __future__ import annotations

from typing import Any, Callable, Dict, Optional, cast

from loguru import logger
from reactivex import Observable, abc

from ..common import (
    create_metadata_tag,
    enrich_metadata,
    is_metadata_tag,
    parse_metadata,
    update_metadata,
)
from ..models import FlvHeader, ScriptTag
from .analyse import KeyFramesDict
from .typing import FLVStream, FLVStreamItem

__all__ = ('Injector',)


class Injector:
    def __init__(
        self, metadata_provider: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        self._metadata_provider = metadata_provider

    def __call__(self, source: FLVStream) -> FLVStream:
        return self._inject(source)

    def _inject(self, source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            index = 0

            def on_next(item: FLVStreamItem) -> None:
                nonlocal index
                if isinstance(item, FlvHeader):
                    index = 0
                    observer.on_next(item)
                    return

                tag = item
                index += 1

                if index == 1:
                    if is_metadata_tag(tag):
                        tag = self._inject_metadata(tag)
                        logger.debug('Injected metadata into the metadata tag')
                    else:
                        logger.debug('No metadata tag in the stream')
                        metadata_tag = self._make_metadata_tag()
                        logger.debug('Maked a metadata tag for metadata injection')
                        observer.on_next(metadata_tag)
                        logger.debug('Inserted the artificial metadata tag')

                observer.on_next(tag)

            return source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    def _inject_metadata(self, tag: ScriptTag) -> ScriptTag:
        old_metadata = parse_metadata(tag)
        new_metadata = self._metadata_provider(old_metadata.copy())
        final_metadata = {
            **{'duration': 0.0, 'filesize': 0.0},
            **old_metadata,
            **new_metadata,
        }
        new_tag = enrich_metadata(tag, final_metadata, offset=tag.offset)

        if 'keyframes' in final_metadata:
            keyframes = cast(KeyFramesDict, final_metadata['keyframes'])
            offset = new_tag.tag_size - tag.tag_size
            keyframes['filepositions'] = list(
                map(lambda p: p + offset, keyframes['filepositions'])
            )
            if 'lastkeyframelocation' in final_metadata:
                final_metadata['lastkeyframelocation'] = keyframes['filepositions'][-1]
            new_tag = update_metadata(new_tag, final_metadata)

        return new_tag

    def _make_metadata_tag(self) -> ScriptTag:
        metadata = self._metadata_provider({})
        metadata = {'duration': 0.0, 'filesize': 0.0, **metadata}
        return create_metadata_tag(metadata)
