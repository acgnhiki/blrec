from __future__ import annotations
import logging
from typing import Optional


from .models import FlvTag, VideoTag
from .exceptions import CutStream
from .common import is_video_nalu_keyframe
from .utils import format_timestamp


__all__ = 'StreamCutter',


logger = logging.getLogger(__name__)


class StreamCutter:
    def __init__(self, min_duration: int = 5_000) -> None:
        self._min_duration = min_duration  # milliseconds
        self._last_position: int = 0
        self.reset()

    @property
    def last_keyframe_tag(self) -> Optional[VideoTag]:
        return self._last_keyframe_tag

    def is_cutting(self) -> bool:
        return self._cutting

    def can_cut_stream(self) -> bool:
        return self._timestamp >= self._min_duration

    def cut_stream(self) -> bool:
        if self.can_cut_stream():
            self._triggered = True
            return True
        return False

    def reset(self) -> None:
        self._cutting = False
        self._triggered = False
        self._timestamp: int = 0
        self._last_keyframe_tag: Optional[VideoTag] = None

    def check_tag(self, tag: FlvTag) -> None:
        self._timestamp = tag.timestamp

        if not self._triggered:
            return

        if not is_video_nalu_keyframe(tag):
            return

        self._last_keyframe_tag = tag
        self._last_position += self._timestamp
        self._cutting = True

        logger.info(f'Cut stream at: {format_timestamp(self._last_position)}')
        raise CutStream()
