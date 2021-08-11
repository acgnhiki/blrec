from __future__ import annotations
import logging
from typing import Optional


from .models import AudioTag, FlvTag, ScriptTag, VideoTag
from .common import (
    is_audio_sequence_header, is_video_sequence_header, is_metadata_tag
)
from .exceptions import AudioParametersChanged, VideoParametersChanged


__all__ = 'ParametersChecker',


logger = logging.getLogger(__name__)


class ParametersChecker:
    def __init__(self) -> None:
        self.reset()

    @property
    def last_metadata_tag(self) -> Optional[ScriptTag]:
        return self._last_metadata_tag

    @property
    def last_audio_header_tag(self) -> Optional[AudioTag]:
        return self._last_audio_header_tag

    @property
    def last_video_header_tag(self) -> Optional[VideoTag]:
        return self._last_video_header_tag

    def reset(self) -> None:
        self._last_metadata_tag: Optional[ScriptTag] = None
        self._last_audio_header_tag: Optional[AudioTag] = None
        self._last_video_header_tag: Optional[VideoTag] = None

    def check_tag(self, tag: FlvTag) -> None:
        if is_audio_sequence_header(tag):
            if self._last_audio_header_tag is not None:
                if not tag.is_the_same_as(self._last_audio_header_tag):
                    logger.warning('Audio parameters changed')
                    self._last_audio_header_tag = tag
                    raise AudioParametersChanged()
            self._last_audio_header_tag = tag
        elif is_video_sequence_header(tag):
            if self._last_video_header_tag is not None:
                if not tag.is_the_same_as(self._last_video_header_tag):
                    logger.warning('Video parameters changed')
                    self._last_video_header_tag = tag
                    raise VideoParametersChanged()
            self._last_video_header_tag = tag
        elif is_metadata_tag(tag):
            self._last_metadata_tag = tag
        else:
            pass
