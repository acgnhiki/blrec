from __future__ import annotations

import io
import logging
from typing import List, Optional, cast

from reactivex import Observable, Subject, abc

from ...utils.ffprobe import StreamProfile, ffprobe
from ..io import FlvWriter
from ..models import FlvHeader, FlvTag
from .typing import FLVStream, FLVStreamItem

__all__ = ('Prober', 'StreamProfile')


logger = logging.getLogger(__name__)


class Prober:
    def __init__(self) -> None:
        self._profiles: Subject[StreamProfile] = Subject()

    def _reset(self) -> None:
        self._gathering: bool = False
        self._gathered_items: List[FLVStreamItem] = []

    @property
    def profiles(self) -> Observable[StreamProfile]:
        return self._profiles

    def __call__(self, source: FLVStream) -> FLVStream:
        return self._probe(source)

    def _probe(self, source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            self._reset()

            def on_next(item: FLVStreamItem) -> None:
                if isinstance(item, FlvHeader):
                    self._gathered_items.clear()
                    self._gathering = True

                if self._gathering:
                    self._gathered_items.append(item)
                    if len(self._gathered_items) >= 10:
                        try:
                            self._do_probe()
                        except Exception as e:
                            logger.warning(f'Failed to probe stream: {repr(e)}')
                        finally:
                            self._gathered_items.clear()
                            self._gathering = False

                observer.on_next(item)

            return source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    def _do_probe(self) -> None:
        bytes_io = io.BytesIO()
        writer = FlvWriter(bytes_io)
        writer.write_header(cast(FlvHeader, self._gathered_items[0]))
        for tag in self._gathered_items[1:]:
            writer.write_tag(cast(FlvTag, tag))

        def on_next(profile: StreamProfile) -> None:
            self._profiles.on_next(profile)

        def on_error(e: Exception) -> None:
            logger.warning(f'Failed to probe stream by ffprobe: {repr(e)}')

        ffprobe(bytes_io.getvalue()).subscribe(on_next, on_error)
