from __future__ import annotations
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Any, Final, Optional, TypeVar, cast
from typing_extensions import TypeGuard

import attr

from ..utils.hash import cksum


class TagType(IntEnum):
    AUDIO = 8
    VIDEO = 9
    SCRIPT = 18


class FrameType(IntEnum):
    KEY_FRAME = 1
    INNER_FRAME = 2
    DISPOSABLE_INNER_FRAME = 3
    GENERATED_KEY_FRAME = 4
    VIDEO_INFO = 5


class CodecID(IntEnum):
    SORENSON_H263 = 2
    SCREEN_VIDEO = 3
    ON2_VP6 = 4
    ON2_VP6_WITH_ALPHA_CHANNEL = 5
    SCREEN_VIDEO_V2 = 6
    AVC = 7


class AVCPacketType(IntEnum):
    AVC_SEQUENCE_HEADER = 0
    AVC_NALU = 1
    AVC_END_OF_SEQENCE = 2


class SoundFormat(IntEnum):
    LINEAR_PCM_PLATFORM_ENDIAN = 0
    ADPCM = 1
    MP3 = 2
    LINEAR_PCM_LITTLE_ENDIAN = 3
    NELLYMOSER_16KHZ_MONO = 4
    NELLYMOSER_8KHZ_MONO = 5
    NELLYMOSER = 6
    G711_A_LAW_LOGARITHMIC_PCM = 7
    G711_MU_LAW_LOGARITHMIC_PCM = 8
    AAC = 10
    SPEEX = 11
    MP3_8KHZ = 14
    DEVICE_SPECIFIC_SOUND = 15


class SoundRate(IntEnum):
    F_5_5KHZ = 0
    F_11KHZ = 1
    F_22KHZ = 2
    F_44KHZ = 3


class SoundSize(IntEnum):
    SAMPLES_8BIT = 0
    SAMPLES_16BIT = 1


class SoundType(IntEnum):
    MONO = 0
    STEREO = 1


class AACPacketType(IntEnum):
    AAC_SEQUENCE_HEADER = 0
    AAC_RAW = 1


def non_negative_integer_validator(instance, attribute, value):  # type: ignore
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"'{attribute}' has to be a non negative integer!")


@attr.s(auto_attribs=True, slots=True, frozen=True)
class FlvHeader:
    signature: str
    version: int
    type_flag: int
    data_offset: int = attr.ib(validator=[non_negative_integer_validator])

    def has_video(self) -> bool:
        return bool(self.type_flag & 0b0000_0001)

    def has_audio(self) -> bool:
        return bool(self.type_flag & 0b0000_0100)

    @property
    def size(self) -> int:
        return self.data_offset


@attr.s(auto_attribs=True, slots=True, frozen=True)
class FlvTagHeader:
    filtered: bool
    tag_type: TagType
    data_size: int = attr.ib(validator=[non_negative_integer_validator])
    timestamp: int = attr.ib(validator=[non_negative_integer_validator])
    stream_id: int = attr.ib(validator=[non_negative_integer_validator])


@attr.s(auto_attribs=True, slots=True, frozen=True)
class AudioTagHeader:
    sound_format: SoundFormat
    sound_rate: SoundRate
    sound_size: SoundSize
    sound_type: SoundType
    aac_packet_type: Optional[AACPacketType]


@attr.s(auto_attribs=True, slots=True, frozen=True)
class VideoTagHeader:
    frame_type: FrameType
    codec_id: CodecID
    avc_packet_type: Optional[AVCPacketType]
    composition_time: Optional[int]


TAG_HEADER_SIZE: Final[int] = 11
BACK_POINTER_SIZE: Final[int] = 4


_T = TypeVar('_T', bound='FlvTag')


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class FlvTag(ABC, FlvTagHeader):
    offset: int = attr.ib(validator=[non_negative_integer_validator])
    body: Optional[bytes] = attr.ib(default=None, repr=cksum)

    @property
    @abstractmethod
    def header_size(self) -> int:
        ...

    @property
    def tag_size(self) -> int:
        return TAG_HEADER_SIZE + self.data_size

    @property
    def body_offset(self) -> int:
        return self.offset + TAG_HEADER_SIZE + self.header_size

    @property
    def body_size(self) -> int:
        return self.data_size - self.header_size

    @property
    def tag_end_offset(self) -> int:
        return self.offset + self.tag_size

    @property
    def next_tag_offset(self) -> int:
        return self.tag_end_offset + BACK_POINTER_SIZE

    def is_audio_tag(self) -> TypeGuard[AudioTag]:
        return self.tag_type == TagType.AUDIO

    def is_video_tag(self) -> TypeGuard[VideoTag]:
        return self.tag_type == TagType.VIDEO

    def is_script_tag(self) -> TypeGuard[ScriptTag]:
        return self.tag_type == TagType.SCRIPT

    def is_the_same_as(self, another: FlvTag) -> bool:
        return (
            self.tag_type == another.tag_type and
            self.data_size == another.data_size and
            self.body == another.body
        )

    def evolve(self: _T, **changes: Any) -> _T:
        if 'body' in changes:
            body = cast(bytes, changes.get('body'))
            changes['data_size'] = self.header_size + len(body)
        return attr.evolve(self, **changes)


# it’s not possible to inherit from more than one class that has attributes in
# __slots__
# ref: https://www.attrs.org/en/stable/glossary.html
# ref: https://docs.python.org/3/reference/datamodel.html#notes-on-using-slots
@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class AudioTag(FlvTag):
    sound_format: SoundFormat
    sound_rate: SoundRate
    sound_size: SoundSize
    sound_type: SoundType
    aac_packet_type: Optional[AACPacketType]

    @property
    def header_size(self) -> int:
        if self.sound_format != SoundFormat.AAC:
            return 1
        else:
            return 2

    def is_aac_format(self) -> bool:
        return self.sound_format == SoundFormat.AAC

    def is_aac_header(self) -> bool:
        return self.aac_packet_type == AACPacketType.AAC_SEQUENCE_HEADER

    def is_aac_raw(self) -> bool:
        return self.aac_packet_type == AACPacketType.AAC_RAW


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class VideoTag(FlvTag):
    frame_type: FrameType
    codec_id: CodecID
    avc_packet_type: Optional[AVCPacketType]
    composition_time: Optional[int]

    @property
    def header_size(self) -> int:
        if self.codec_id != CodecID.AVC:
            return 1
        else:
            return 5

    def is_avc_header(self) -> bool:
        return self.avc_packet_type == AVCPacketType.AVC_SEQUENCE_HEADER

    def is_avc_nalu(self) -> bool:
        return self.avc_packet_type == AVCPacketType.AVC_NALU

    def is_avc_end(self) -> bool:
        return self.avc_packet_type == AVCPacketType.AVC_END_OF_SEQENCE

    def is_keyframe(self) -> bool:
        return self.frame_type == FrameType.KEY_FRAME


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class ScriptTag(FlvTag):
    @property
    def header_size(self) -> int:
        return 0
