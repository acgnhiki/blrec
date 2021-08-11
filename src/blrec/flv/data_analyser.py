"""
Analyse FLV file to make MetaData
ref: https://github.com/ioppermann/yamdi/blob/master/yamdi.c
"""
from __future__ import annotations
from typing import List, Optional

import attr

from .models import (
    AudioTag, FlvHeader, FlvTag, SoundType, VideoTag, ScriptTag,
    BACK_POINTER_SIZE
)
from .common import Resolution, is_audio_tag, is_script_tag, is_video_tag


__all__ = 'DataAnalyser',


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class KeyFrames:
    times: List[float]
    filepositions: List[float]


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class MetaData:
    hasAudio: bool
    hasVideo: bool
    hasMetadata: bool
    hasKeyframes: bool
    canSeekToEnd: bool
    duration: float
    datasize: float
    filesize: float

    audiosize: Optional[float] = None
    audiocodecid: Optional[float] = None
    audiodatarate: Optional[float] = None
    audiosamplerate: Optional[float] = None
    audiosamplesize: Optional[float] = None
    stereo: Optional[bool] = None

    videosize: float
    framerate: float
    videocodecid: float
    videodatarate: float
    width: float
    height: float

    lasttimestamp: float
    lastkeyframelocation: float
    lastkeyframetimestamp: float
    keyframes: KeyFrames


class DataAnalyser:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._num_of_tags = 0
        self._num_of_audio_tags = 0
        self._num_of_video_tags = 0
        self._size_of_tags = 0
        self._size_of_audio_tags = 0
        self._size_of_video_tags = 0
        self._size_of_data = 0
        self._size_of_audio_data = 0
        self._size_of_video_data = 0
        self._last_timestamp = 0
        self._last_timestamp_of_audio = 0
        self._last_timestamp_of_video = 0
        self._keyframe_timestamps: List[int] = []
        self._keyframe_filepositions: List[int] = []
        self._resolution: Optional[Resolution] = None

        self._header_analysed = False
        self._audio_analysed = False
        self._video_analysed = False

    def analyse_header(self, header: FlvHeader) -> None:
        assert not self._header_analysed
        self._header_analysed = True
        self._size_of_flv_header = header.size
        self._has_audio = header.has_audio()
        self._has_video = header.has_video()

    def analyse_tag(self, tag: FlvTag) -> None:
        if is_audio_tag(tag):
            self._analyse_audio_tag(tag)
        elif is_video_tag(tag):
            self._analyse_video_tag(tag)
        elif is_script_tag(tag):
            self._analyse_script_tag(tag)
        else:
            raise ValueError('Invalid tag type')

        self._num_of_tags += 1
        self._size_of_tags += tag.tag_size
        self._size_of_data += tag.data_size
        self._last_timestamp = tag.timestamp

    def get_real_resolution(self) -> Optional[Resolution]:
        return self._resolution

    def calc_frame_rate(self) -> float:
        try:
            return (
                self._num_of_video_tags / self._last_timestamp_of_video * 1000
            )
        except ZeroDivisionError:
            return 0.0

    def calc_audio_data_rate(self) -> float:
        try:
            return self._size_of_audio_data * 8 / self._last_timestamp_of_audio
        except ZeroDivisionError:
            return 0.0

    def calc_video_data_rate(self) -> float:
        try:
            return self._size_of_video_data * 8 / self._last_timestamp_of_video
        except ZeroDivisionError:
            return 0.0

    def calc_data_size(self) -> int:
        return (
            self._size_of_audio_tags +
            self._num_of_audio_tags * BACK_POINTER_SIZE +
            self._size_of_video_tags +
            self._num_of_video_tags * BACK_POINTER_SIZE
        )

    def calc_file_size(self) -> int:
        return (
            self._size_of_flv_header + BACK_POINTER_SIZE +
            self._size_of_tags + self._num_of_tags * BACK_POINTER_SIZE
        )

    def make_keyframes(self) -> KeyFrames:
        return KeyFrames(
            times=list(map(lambda t: t / 1000, self._keyframe_timestamps)),
            filepositions=list(map(float, self._keyframe_filepositions)),
        )

    def make_metadata(self) -> MetaData:
        assert self._header_analysed
        assert self._has_audio == self._audio_analysed
        assert self._has_video and self._video_analysed
        assert self._resolution is not None

        if not self._has_audio:
            audiosize = None
            audiocodecid = None
            audiodatarate = None
            audiosamplerate = None
            audiosamplesize = None
            stereo = None
        else:
            audiosize = float(self._size_of_audio_tags)
            audiocodecid = float(self._audio_codec_id)
            audiodatarate = self.calc_audio_data_rate()
            audiosamplerate = float(self._audio_sample_rate)
            audiosamplesize = float(self._audio_sample_size)
            stereo = self._stereo

        keyframes = self.make_keyframes()

        return MetaData(
            hasAudio=self._has_audio,
            hasVideo=self._has_video,
            hasMetadata=True,
            hasKeyframes=len(self._keyframe_timestamps) != 0,
            canSeekToEnd=(
                self._last_timestamp_of_video == self._keyframe_timestamps[-1]
            ),
            duration=self._last_timestamp / 1000,
            datasize=float(self.calc_data_size()),
            filesize=float(self.calc_file_size()),
            audiosize=audiosize,
            audiocodecid=audiocodecid,
            audiodatarate=audiodatarate,
            audiosamplerate=audiosamplerate,
            audiosamplesize=audiosamplesize,
            stereo=stereo,
            videosize=float(self._size_of_video_tags),
            framerate=self.calc_frame_rate(),
            videocodecid=float(self._video_codec_id),
            videodatarate=self.calc_video_data_rate(),
            width=float(self._resolution.width),
            height=float(self._resolution.height),
            lasttimestamp=self._last_timestamp / 1000,
            lastkeyframelocation=keyframes.filepositions[-1],
            lastkeyframetimestamp=keyframes.times[-1],
            keyframes=keyframes,
        )

    def _analyse_audio_tag(self, tag: AudioTag) -> None:
        if not self._audio_analysed:
            self._audio_analysed = True
            self._audio_codec_id = tag.sound_format.value
            self._audio_sample_rate = tag.sound_rate.value
            self._audio_sample_size = tag.sound_size.value
            self._stereo = tag.sound_type == SoundType.STEREO

        self._num_of_audio_tags += 1
        self._size_of_audio_tags += tag.tag_size
        self._size_of_audio_data += tag.data_size
        self._last_timestamp_of_audio = tag.timestamp

    def _analyse_video_tag(self, tag: VideoTag) -> None:
        if tag.is_keyframe():
            self._keyframe_timestamps.append(tag.timestamp)
            self._keyframe_filepositions.append(tag.offset)
            if tag.is_avc_header():
                self._resolution = Resolution.from_aac_sequence_header(tag)
        else:
            pass

        if not self._video_analysed:
            self._video_analysed = True
            self._video_codec_id = tag.codec_id.value

        self._num_of_video_tags += 1
        self._size_of_video_tags += tag.tag_size
        self._size_of_video_data += tag.data_size
        self._last_timestamp_of_video = tag.timestamp

    def _analyse_script_tag(self, tag: ScriptTag) -> None:
        pass
