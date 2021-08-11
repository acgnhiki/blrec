from typing import cast

import attr

from .struct_io import StructReader, StructWriter
from .io_protocols import RandomIO
from .models import (
    FlvTag,
    TagType,
    FlvHeader,
    FlvTagHeader,

    AudioTag,
    AudioTagHeader,
    SoundFormat,
    SoundRate,
    SoundSize,
    SoundType,
    AACPacketType,

    VideoTag,
    VideoTagHeader,
    CodecID,
    FrameType,
    AVCPacketType,

    ScriptTag,
)


__all__ = 'FlvParser', 'FlvDumper'


class FlvParser:
    def __init__(self, stream: RandomIO) -> None:
        self._stream = stream
        self._reader = StructReader(stream)

    def parse_header(self) -> FlvHeader:
        signature = self._reader.read(3).decode()
        assert signature == 'FLV', 'Not a FLV file'
        version = self._reader.read_ui8()
        type_flag = self._reader.read_ui8()
        data_offset = self._reader.read_ui32()
        return FlvHeader(signature, version, type_flag, data_offset)

    def parse_previous_tag_size(self) -> int:
        return self._reader.read_ui32()

    def parse_tag(self, *, no_body: bool = False) -> FlvTag:
        offset = self._stream.tell()
        tag_header = self.parse_flv_tag_header()

        tag: FlvTag
        arguments = dict(attr.asdict(tag_header), offset=offset)

        if tag_header.tag_type == TagType.AUDIO:
            audio_tag_header = self.parse_audio_tag_header()
            arguments.update(attr.asdict(audio_tag_header))
            tag = AudioTag(**arguments)
        elif tag_header.tag_type == TagType.VIDEO:
            video_tag_header = self.parse_video_tag_header()
            arguments.update(attr.asdict(video_tag_header))
            tag = VideoTag(**arguments)
        elif tag_header.tag_type == TagType.SCRIPT:
            tag = ScriptTag(**arguments)
        else:
            raise ValueError(tag_header.tag_type)

        if no_body:
            self._stream.seek(tag.tag_end_offset)
        else:
            body = self._reader.read(tag.body_size)
            tag = tag.evolve(body=body)

        return tag

    def parse_flv_tag_header(self) -> FlvTagHeader:
        flag = self._reader.read_ui8()
        filtered = bool(flag & 0b0010_0000)
        assert not filtered, 'Unsupported Filtered FLV Tag'
        tag_type = TagType(flag & 0b0001_1111)
        data_size = self._reader.read_ui24()
        assert data_size > 0, 'Invalid Tag'
        timestamp = self._reader.read_ui24()
        timestamp_extended = self._reader.read_ui8()
        timestamp = timestamp_extended << 24 | timestamp
        stream_id = self._reader.read_ui24()
        return FlvTagHeader(
            filtered, tag_type, data_size, timestamp, stream_id
        )

    def parse_audio_tag_header(self) -> AudioTagHeader:
        flag = self._reader.read_ui8()
        sound_format = SoundFormat(flag >> 4)
        sound_rate = SoundRate((flag >> 2) & 0b0000_0011)
        sound_size = SoundSize((flag >> 1) & 0b0000_0001)
        sound_type = SoundType(flag & 0b0000_0001)

        if sound_format != SoundFormat.AAC:
            aac_packet_type = None
        else:
            aac_packet_type = AACPacketType(self._reader.read_ui8())

        return AudioTagHeader(
            sound_format, sound_rate, sound_size, sound_type, aac_packet_type
        )

    def parse_video_tag_header(self) -> VideoTagHeader:
        flag = self._reader.read_ui8()
        frame_type = FrameType(flag >> 4)
        codec_id = CodecID(flag & 0b0000_1111)

        if codec_id != CodecID.AVC:
            avc_packet_type = None
            composition_time = None
        else:
            avc_packet_type = AVCPacketType(self._reader.read_ui8())
            composition_time = self._reader.read_ui24()

        return VideoTagHeader(
            frame_type, codec_id, avc_packet_type, composition_time
        )


class FlvDumper:
    def __init__(self, stream: RandomIO) -> None:
        self._stream = stream
        self._writer = StructWriter(stream)

    def dump_header(self, flv_header: FlvHeader) -> None:
        self._writer.write(flv_header.signature.encode())
        self._writer.write_ui8(flv_header.version)
        self._writer.write_ui8(flv_header.type_flag)
        self._writer.write_ui32(flv_header.data_offset)

    def dump_previous_tag_size(self, size: int) -> None:
        self._writer.write_ui32(size)

    def dump_tag(self, tag: FlvTag) -> None:
        self.dump_flv_tag_header(tag)

        if tag.is_audio_tag():
            audio_tag = cast(AudioTag, tag)
            self.dump_audio_tag_header(audio_tag)
        elif tag.is_video_tag():
            video_tag = cast(VideoTag, tag)
            self.dump_video_tag_header(video_tag)
        elif tag.is_script_tag():
            pass
        else:
            raise ValueError(tag.tag_type)

        if tag.body is None:
            self._stream.seek(tag.tag_end_offset)
        else:
            self._writer.write(tag.body)

    def dump_flv_tag_header(self, tag: FlvTag) -> None:
        self._writer.write_ui8((int(tag.filtered) << 5) | tag.tag_type.value)
        self._writer.write_ui24(tag.data_size)
        self._writer.write_ui24(tag.timestamp & 0x00ffffff)
        self._writer.write_ui8(tag.timestamp >> 24)
        self._writer.write_ui24(tag.stream_id)

    def dump_audio_tag_header(self, tag: AudioTag) -> None:
        self._writer.write_ui8(
            (tag.sound_format.value << 4) |
            (tag.sound_rate.value << 2) |
            (tag.sound_size.value << 1) |
            tag.sound_type.value
        )
        if tag.aac_packet_type is not None:
            assert tag.sound_format == SoundFormat.AAC
            self._writer.write_ui8(tag.aac_packet_type)

    def dump_video_tag_header(self, tag: VideoTag) -> None:
        self._writer.write_ui8(
            (tag.frame_type.value << 4) | tag.codec_id.value
        )
        if tag.codec_id == CodecID.AVC:
            assert tag.avc_packet_type is not None
            assert tag.composition_time is not None
            self._writer.write_ui8(tag.avc_packet_type.value)
            self._writer.write_ui24(tag.composition_time)
