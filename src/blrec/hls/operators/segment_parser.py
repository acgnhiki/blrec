from __future__ import annotations

import io
import logging
from typing import Optional

from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from blrec.flv.common import (
    is_audio_sequence_header,
    is_metadata_tag,
    is_video_sequence_header,
)
from blrec.flv.io import FlvReader
from blrec.flv.models import AudioTag, FlvHeader, ScriptTag, VideoTag
from blrec.flv.operators.typing import FLVStream, FLVStreamItem

__all__ = ('SegmentParser',)


logger = logging.getLogger(__name__)


class SegmentParser:
    def __init__(self) -> None:
        self._backup_timestamp = True

    def __call__(self, source: Observable[bytes]) -> FLVStream:
        return self._parse(source)

    def _parse(self, source: Observable[bytes]) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            last_flv_header: Optional[FlvHeader] = None
            last_metadata_tag: Optional[ScriptTag] = None
            last_audio_sequence_header: Optional[AudioTag] = None
            last_video_sequence_header: Optional[VideoTag] = None

            def reset() -> None:
                nonlocal last_flv_header, last_metadata_tag
                nonlocal last_audio_sequence_header, last_video_sequence_header
                last_flv_header = None
                last_metadata_tag = None
                last_audio_sequence_header = None
                last_video_sequence_header = None

            def on_next(data: bytes) -> None:
                nonlocal last_flv_header, last_metadata_tag
                nonlocal last_audio_sequence_header, last_video_sequence_header

                if b'' == data:
                    reset()
                    return

                try:
                    reader = FlvReader(
                        io.BytesIO(data), backup_timestamp=self._backup_timestamp
                    )

                    flv_header = reader.read_header()
                    if not last_flv_header:
                        observer.on_next(flv_header)
                        last_flv_header = flv_header
                    else:
                        assert last_flv_header == flv_header

                    while not disposed:
                        tag = reader.read_tag()
                        if is_metadata_tag(tag):
                            if last_metadata_tag is not None:
                                continue
                            last_metadata_tag = tag
                        elif is_video_sequence_header(tag):
                            if tag == last_video_sequence_header:
                                continue
                            last_video_sequence_header = tag
                        elif is_audio_sequence_header(tag):
                            if tag == last_audio_sequence_header:
                                continue
                            last_audio_sequence_header = tag
                        observer.on_next(tag)
                except EOFError:
                    pass
                except Exception as e:
                    observer.on_error(e)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                reset()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
