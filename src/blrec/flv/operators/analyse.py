"""
Analyse the FLV stream to make MetaData
ref: https://github.com/ioppermann/yamdi/blob/master/yamdi.c
"""
from __future__ import annotations

from typing import List, Optional, TypedDict

import attr
from loguru import logger
from reactivex import Observable, Subject, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from ..common import Resolution, is_audio_tag, is_script_tag, is_video_tag
from ..models import (
    BACK_POINTER_SIZE,
    AudioTag,
    FlvHeader,
    FlvTag,
    ScriptTag,
    SoundType,
    VideoTag,
)
from .typing import FLVStream, FLVStreamItem

__all__ = 'Analyser', 'MetaData', 'KeyFrames'


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class KeyFrames:
    times: List[float]
    filepositions: List[float]


class KeyFramesDict(TypedDict):
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


class MetaDataDict:
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
    keyframes: KeyFramesDict


class Analyser:
    def __init__(self) -> None:
        self._metadatas: Subject[Optional[MetaData]] = Subject()
        self._duration_updated: Subject[float] = Subject()
        self._reset()

    def _reset(self) -> None:
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

        self._has_audio = False
        self._has_video = False
        self._audio_analysed = False
        self._video_analysed = False

    @property
    def duration(self) -> float:
        return self._last_timestamp / 1000

    @property
    def metadatas(self) -> Observable[Optional[MetaData]]:
        return self._metadatas

    @property
    def duration_updated(self) -> Observable[float]:
        return self._duration_updated

    def __call__(self, source: FLVStream) -> FLVStream:
        return self._analyse(source)

    def get_real_resolution(self) -> Optional[Resolution]:
        return self._resolution

    def calc_frame_rate(self) -> float:
        try:
            return self._num_of_video_tags / self._last_timestamp_of_video * 1000
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
            self._size_of_audio_tags
            + self._num_of_audio_tags * BACK_POINTER_SIZE
            + self._size_of_video_tags
            + self._num_of_video_tags * BACK_POINTER_SIZE
        )

    def calc_file_size(self) -> int:
        return (
            self._size_of_flv_header
            + BACK_POINTER_SIZE
            + self._size_of_tags
            + self._num_of_tags * BACK_POINTER_SIZE
        )

    def make_keyframes(self) -> KeyFrames:
        return KeyFrames(
            times=list(map(lambda t: t / 1000, self._keyframe_timestamps)),
            filepositions=list(map(float, self._keyframe_filepositions)),
        )

    def make_metadata(self) -> MetaData:
        assert self._has_audio == self._audio_analysed, (
            f'has_audio: {self._has_audio}, audio_analysed: {self._audio_analysed}',
        )
        assert self._has_video and self._video_analysed, (
            f'has_video: {self._has_video}, video_analysed: {self._video_analysed}',
        )
        assert self._resolution is not None, 'no resolution'

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

    def _analyse(self, source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            self._reset()
            stream_index: int = -1

            def push_metadata() -> None:
                try:
                    metadata = self.make_metadata()
                except Exception as e:
                    logger.warning(f'Failed to make metadata: {repr(e)}')
                    self._metadatas.on_next(None)
                else:
                    self._metadatas.on_next(metadata)

            def on_next(item: FLVStreamItem) -> None:
                nonlocal stream_index
                if isinstance(item, FlvHeader):
                    stream_index += 1
                    if stream_index > 0:
                        push_metadata()
                    self._reset()
                    self._analyse_flv_header(item)
                else:
                    self._analyse_tag(item)
                observer.on_next(item)

            def on_completed() -> None:
                push_metadata()
                observer.on_completed()

            def on_error(e: Exception) -> None:
                push_metadata()
                observer.on_error(e)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                push_metadata()
                self._reset()

            subscription.disposable = source.subscribe(
                on_next, on_error, on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    def _analyse_flv_header(self, header: FlvHeader) -> None:
        self._size_of_flv_header = header.size

    def _analyse_tag(self, tag: FlvTag) -> None:
        if is_audio_tag(tag):
            self._analyse_audio_tag(tag)
        elif is_video_tag(tag):
            self._analyse_video_tag(tag)
        elif is_script_tag(tag):
            self._analyse_script_tag(tag)
        else:
            logger.warning(f'Invalid tag type: {tag}')

        self._num_of_tags += 1
        self._size_of_tags += tag.tag_size
        self._size_of_data += tag.data_size
        self._last_timestamp = tag.timestamp
        self._duration_updated.on_next(self._last_timestamp / 1000)

    def _analyse_audio_tag(self, tag: AudioTag) -> None:
        if not self._audio_analysed:
            self._has_audio = True
            self._audio_analysed = True
            self._audio_codec_id = tag.sound_format.value
            self._audio_sample_rate = tag.sound_rate.value
            self._audio_sample_size = tag.sound_size.value
            self._stereo = tag.sound_type == SoundType.STEREO
            logger.debug(f'Audio analysed: {tag}')

        self._num_of_audio_tags += 1
        self._size_of_audio_tags += tag.tag_size
        self._size_of_audio_data += tag.data_size
        self._last_timestamp_of_audio = tag.timestamp

    def _analyse_video_tag(self, tag: VideoTag) -> None:
        if tag.is_keyframe():
            self._keyframe_timestamps.append(tag.timestamp)
            self._keyframe_filepositions.append(self.calc_file_size())
            if tag.is_avc_header():
                self._resolution = Resolution.from_avc_sequence_header(tag)
                logger.debug(f'Resolution: {self._resolution}')
        else:
            pass

        if not self._video_analysed:
            self._has_video = True
            self._video_analysed = True
            self._video_codec_id = tag.codec_id.value
            logger.debug(f'Video analysed: {tag}')

        self._num_of_video_tags += 1
        self._size_of_video_tags += tag.tag_size
        self._size_of_video_data += tag.data_size
        self._last_timestamp_of_video = tag.timestamp

    def _analyse_script_tag(self, tag: ScriptTag) -> None:
        pass
