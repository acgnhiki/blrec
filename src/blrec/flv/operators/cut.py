from __future__ import annotations

from typing import Optional

from loguru import logger
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from ..common import (
    is_audio_sequence_header,
    is_metadata_tag,
    is_video_nalu_keyframe,
    is_video_sequence_header,
)
from ..models import AudioTag, FlvHeader, FlvTag, ScriptTag, VideoTag
from ..utils import format_timestamp
from .correct import correct
from .typing import FLVStream, FLVStreamItem

__all__ = ('Cutter',)


class Cutter:
    def __init__(self, min_duration: int = 5_000) -> None:
        self._min_duration = min_duration  # milliseconds
        self._reset()

    def _reset(self) -> None:
        self._cutting: bool = False
        self._triggered: bool = False
        self._last_timestamp: int = 0
        self._last_flv_header: Optional[FlvHeader] = None
        self._last_metadata_tag: Optional[ScriptTag] = None
        self._last_audio_sequence_header: Optional[AudioTag] = None
        self._last_video_sequence_header: Optional[VideoTag] = None

    def is_cutting(self) -> bool:
        return self._cutting

    def can_cut_stream(self) -> bool:
        if self._triggered or self._cutting:
            return False
        return self._last_timestamp >= self._min_duration

    def cut_stream(self) -> bool:
        if self.can_cut_stream():
            self._triggered = True
            return True
        return False

    def __call__(self, source: FLVStream) -> FLVStream:
        return self._cut(source).pipe(correct())

    def _cut(self, source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            def on_next(item: FLVStreamItem) -> None:
                if isinstance(item, FlvHeader):
                    self._reset()
                    self._update_flv_header(item)
                else:
                    self._update_meta_tags(item)
                    self._check_cut_point(item)
                    if self._cutting:
                        self._insert_header_and_tags(observer)
                        self._cutting = False
                        self._triggered = False
                observer.on_next(item)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                self._reset()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    def _update_flv_header(self, header: FlvHeader) -> None:
        self._last_flv_header = header

    def _update_meta_tags(self, tag: FlvTag) -> None:
        if is_metadata_tag(tag):
            self._last_metadata_tag = tag
        elif is_audio_sequence_header(tag):
            self._last_audio_sequence_header = tag
        elif is_video_sequence_header(tag):
            self._last_video_sequence_header = tag

    def _insert_header_and_tags(
        self, observer: abc.ObserverBase[FLVStreamItem]
    ) -> None:
        assert self._last_flv_header is not None
        observer.on_next(self._last_flv_header)
        if self._last_metadata_tag is not None:
            observer.on_next(self._last_metadata_tag)
        if self._last_video_sequence_header is not None:
            observer.on_next(self._last_video_sequence_header)
        if self._last_audio_sequence_header is not None:
            observer.on_next(self._last_audio_sequence_header)

    def _check_cut_point(self, tag: FlvTag) -> None:
        self._last_timestamp = tag.timestamp

        if not self._triggered:
            return

        if not is_video_nalu_keyframe(tag):
            return

        self._cutting = True
        logger.info(f'Cut stream at {format_timestamp(tag.timestamp)}')
