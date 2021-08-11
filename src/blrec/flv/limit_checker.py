from __future__ import annotations
import logging
from typing import Optional


from .models import FlvHeader, FlvTag, BACK_POINTER_SIZE, VideoTag
from .exceptions import FileSizeOverLimit, DurationOverLimit
from .common import is_video_nalu_keyframe


__all__ = 'LimitChecker',


logger = logging.getLogger(__name__)


class LimitChecker:
    def __init__(
        self,
        filesize_limit: int = 0,  # file size in bytes, no limit by default.
        duration_limit: int = 0,  # duration in seconds, no limit by default.
    ) -> None:
        self.filesize_limit = filesize_limit
        self.duration_limit = duration_limit
        self.reset()

    def is_filesize_over_limit(self) -> bool:
        return (
            self._filesize + self._max_size_between_keyframes >=
            self.filesize_limit
        )

    def is_duration_over_limit(self) -> bool:
        return (
            self._duration + self._max_duration_between_keyframes >=
            self.duration_limit
        )

    @property
    def last_keyframe_tag(self) -> Optional[VideoTag]:
        return self._last_keyframe_tag

    def reset(self) -> None:
        self._filesize = 0
        self._duration = 0.0
        self._max_size_between_keyframes = 0
        self._max_duration_between_keyframes = 0.0
        self._header_checked = False
        self._last_keyframe_tag: Optional[VideoTag] = None

    def check_header(self, header: FlvHeader) -> None:
        assert not self._header_checked
        self._header_checked = True
        self._filesize += header.size + BACK_POINTER_SIZE

    def check_tag(self, tag: FlvTag) -> None:
        self._filesize += tag.tag_size + BACK_POINTER_SIZE
        self._duration = tag.timestamp / 1000

        if not is_video_nalu_keyframe(tag):
            return

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

        if self.filesize_limit > 0 and self.is_filesize_over_limit():
            logger.debug('File size will be over the limit: {} + {}'.format(
                self._filesize, self._max_size_between_keyframes,
            ))
            raise FileSizeOverLimit()

        if self.duration_limit > 0 and self.is_duration_over_limit():
            logger.debug('Duration will be over the limit: {} + {}'.format(
                self._duration, self._max_duration_between_keyframes,
            ))
            raise DurationOverLimit()
