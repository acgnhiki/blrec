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
from ..models import BACK_POINTER_SIZE, AudioTag, FlvHeader, FlvTag, ScriptTag, VideoTag
from .correct import correct
from .typing import FLVStream, FLVStreamItem

__all__ = ('Limiter',)


class Limiter:
    def __init__(
        self,
        filesize_limit: int = 0,  # file size in bytes, no limit by default.
        duration_limit: int = 0,  # duration in seconds, no limit by default.
    ) -> None:
        self.filesize_limit = filesize_limit
        self.duration_limit = duration_limit
        self._reset()

    def _reset(self) -> None:
        self._filesize: int = 0
        self._duration: float = 0.0
        self._max_size_between_keyframes: int = 0
        self._max_duration_between_keyframes: float = 0.0
        self._first_keyframe_tag: Optional[VideoTag] = None
        self._last_keyframe_tag: Optional[VideoTag] = None
        self._last_flv_header: Optional[FlvHeader] = None
        self._last_metadata_tag: Optional[ScriptTag] = None
        self._last_audio_sequence_header: Optional[AudioTag] = None
        self._last_video_sequence_header: Optional[VideoTag] = None

    def __call__(self, source: FLVStream) -> FLVStream:
        return self._limit(source).pipe(correct())

    def _limit(self, source: FLVStream) -> FLVStream:
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
                    will_over_limts = self._check_limits(item)
                    if will_over_limts:
                        self._insert_header_and_tags(observer)
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

        self._filesize = self._last_flv_header.size
        if self._last_metadata_tag is not None:
            self._filesize += self._last_metadata_tag.tag_size
        if self._last_video_sequence_header is not None:
            self._filesize += self._last_video_sequence_header.tag_size
        if self._last_audio_sequence_header is not None:
            self._filesize += self._last_audio_sequence_header.tag_size
        self._duration = 0.0
        self._first_keyframe_tag = self._last_keyframe_tag

    def _will_filesize_over_limit(self) -> bool:
        return self._filesize + self._max_size_between_keyframes >= self.filesize_limit

    def _will_duration_over_limit(self) -> bool:
        return (
            self._duration + self._max_duration_between_keyframes >= self.duration_limit
        )

    def _update_flv_header(self, header: FlvHeader) -> None:
        self._filesize += header.size + BACK_POINTER_SIZE
        self._last_flv_header = header

    def _update_meta_tags(self, tag: FlvTag) -> None:
        if is_metadata_tag(tag):
            self._last_metadata_tag = tag
        elif is_audio_sequence_header(tag):
            self._last_audio_sequence_header = tag
        elif is_video_sequence_header(tag):
            self._last_video_sequence_header = tag

    def _check_limits(self, tag: FlvTag) -> bool:
        self._filesize += tag.tag_size + BACK_POINTER_SIZE

        if not is_video_nalu_keyframe(tag):
            return False

        if self._first_keyframe_tag is None:
            self._first_keyframe_tag = tag

        if self._last_keyframe_tag is not None:
            self._max_size_between_keyframes = max(
                self._max_size_between_keyframes,
                tag.offset - self._last_keyframe_tag.offset,
            )
            self._max_duration_between_keyframes = max(
                self._max_duration_between_keyframes,
                (tag.timestamp - self._last_keyframe_tag.timestamp) / 1000,
            )

        self._last_keyframe_tag = tag
        self._duration = (
            self._last_keyframe_tag.timestamp - self._first_keyframe_tag.timestamp
        ) / 1000

        if self.filesize_limit > 0 and self._will_filesize_over_limit():
            logger.debug(
                'File size will be over the limit: {} + {}'.format(
                    self._filesize, self._max_size_between_keyframes
                )
            )
            return True

        if self.duration_limit > 0 and self._will_duration_over_limit():
            logger.debug(
                'Duration will be over the limit: {} + {}'.format(
                    self._duration, self._max_duration_between_keyframes
                )
            )
            return True

        return False
