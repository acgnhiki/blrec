from io import SEEK_CUR, BytesIO
from typing import cast

import attr

from .exceptions import FlvDataError, FlvHeaderError, FlvTagError
from .io_protocols import RandomIO
from .models import (
    AUDIO_TAG_HEADER_SIZE,
    TAG_HEADER_SIZE,
    VIDEO_TAG_HEADER_SIZE,
    AACPacketType,
    AudioTag,
    AudioTagHeader,
    AVCPacketType,
    CodecID,
    FlvHeader,
    FlvTag,
    FlvTagHeader,
    FrameType,
    ScriptTag,
    SoundFormat,
    SoundRate,
    SoundSize,
    SoundType,
    TagType,
    VideoTag,
    VideoTagHeader,
)
from .struct_io import StructReader, StructWriter

__all__ = 'FlvParser', 'FlvDumper'


class FlvParser:
    def __init__(
        self,
        stream: RandomIO,
        backup_timestamp: bool = False,
        restore_timestamp: bool = False,
    ) -> None:
        self._stream = stream
        self._backup_timestamp = backup_timestamp
        self._restore_timestamp = restore_timestamp
        self._reader = StructReader(stream)

    def parse_header(self) -> FlvHeader:
        signature = self._reader.read(3).decode()
        if signature != 'FLV':
            raise FlvHeaderError(signature)
        version = self._reader.read_ui8()
        type_flag = self._reader.read_ui8()
        data_offset = self._reader.read_ui32()
        return FlvHeader(signature, version, type_flag, data_offset)

    def parse_previous_tag_size(self) -> int:
        return self._reader.read_ui32()

    def parse_tag(self, *, no_body: bool = False) -> FlvTag:
        offset = self._stream.tell()
        tag_header_data = self._reader.read(TAG_HEADER_SIZE)
        tag_header = self.parse_flv_tag_header(tag_header_data)

        if tag_header.data_size <= 0:
            raise FlvTagError('No tag data', tag_header)

        if tag_header.tag_type == TagType.AUDIO:
            header_data = self._reader.read(AUDIO_TAG_HEADER_SIZE)
            body_size = tag_header.data_size - AUDIO_TAG_HEADER_SIZE
            if no_body:
                self._stream.seek(body_size, SEEK_CUR)
                body = b''
            else:
                body = self._reader.read(body_size)
            audio_tag_header = self.parse_audio_tag_header(header_data)
            return AudioTag(
                offset=offset,
                **attr.asdict(tag_header),
                **attr.asdict(audio_tag_header),
                body=body,
            )
        elif tag_header.tag_type == TagType.VIDEO:
            header_data = self._reader.read(VIDEO_TAG_HEADER_SIZE)
            body_size = tag_header.data_size - VIDEO_TAG_HEADER_SIZE
            if no_body:
                self._stream.seek(body_size, SEEK_CUR)
                body = b''
            else:
                body = self._reader.read(body_size)
            video_tag_header = self.parse_video_tag_header(header_data)
            return VideoTag(
                offset=offset,
                **attr.asdict(tag_header),
                **attr.asdict(video_tag_header),
                body=body,
            )
        elif tag_header.tag_type == TagType.SCRIPT:
            body_size = tag_header.data_size
            if no_body:
                self._stream.seek(body_size, SEEK_CUR)
                body = b''
            else:
                body = self._reader.read(body_size)
            return ScriptTag(offset=offset, **attr.asdict(tag_header), body=body)
        else:
            raise FlvDataError(f'Unsupported tag type: {tag_header.tag_type}')

    def parse_flv_tag_header(self, data: bytes) -> FlvTagHeader:
        reader = StructReader(BytesIO(data))

        flag = reader.read_ui8()
        filtered = bool(flag & 0b0010_0000)
        if filtered:
            raise FlvDataError('Unsupported Filtered FLV Tag', data)

        tag_type = TagType(flag & 0b0001_1111)
        data_size = reader.read_ui24()
        timestamp = reader.read_ui24()
        timestamp_extended = reader.read_ui8()
        stream_id = reader.read_ui24()

        if self._backup_timestamp:
            return FlvTagHeader(
                filtered=filtered,
                tag_type=tag_type,
                data_size=data_size,
                timestamp=timestamp_extended << 24 | timestamp,
                stream_id=timestamp,
            )
        elif self._restore_timestamp:
            return FlvTagHeader(
                filtered=filtered,
                tag_type=tag_type,
                data_size=data_size,
                timestamp=stream_id,
                stream_id=stream_id,
            )
        else:
            return FlvTagHeader(
                filtered=filtered,
                tag_type=tag_type,
                data_size=data_size,
                timestamp=timestamp_extended << 24 | timestamp,
                stream_id=stream_id,
            )

    def parse_audio_tag_header(self, data: bytes) -> AudioTagHeader:
        reader = StructReader(BytesIO(data))
        flag = reader.read_ui8()
        sound_format = SoundFormat(flag >> 4)
        if sound_format != SoundFormat.AAC:
            raise FlvDataError(f'Unsupported sound format: {sound_format}', data)
        sound_rate = SoundRate((flag >> 2) & 0b0000_0011)
        sound_size = SoundSize((flag >> 1) & 0b0000_0001)
        sound_type = SoundType(flag & 0b0000_0001)
        aac_packet_type = AACPacketType(reader.read_ui8())
        return AudioTagHeader(
            sound_format, sound_rate, sound_size, sound_type, aac_packet_type
        )

    def parse_video_tag_header(self, data: bytes) -> VideoTagHeader:
        reader = StructReader(BytesIO(data))
        flag = reader.read_ui8()
        frame_type = FrameType(flag >> 4)
        codec_id = CodecID(flag & 0b0000_1111)
        if codec_id != CodecID.AVC:
            raise FlvDataError(f'Unsupported video codec: {codec_id}', data)
        avc_packet_type = AVCPacketType(reader.read_ui8())
        composition_time = reader.read_ui24()
        return VideoTagHeader(frame_type, codec_id, avc_packet_type, composition_time)


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
        if tag.timestamp < 0:
            raise FlvDataError(f'Incorrect timestamp: {tag.timestamp}', tag)

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
            raise FlvDataError(f'Unsupported tag type: {tag.tag_type}')

        if tag.body:
            self._writer.write(tag.body)
        else:
            self._stream.seek(tag.tag_end_offset)

    def dump_flv_tag_header(self, tag: FlvTag) -> None:
        self._writer.write_ui8((int(tag.filtered) << 5) | tag.tag_type.value)
        self._writer.write_ui24(tag.data_size)
        self._writer.write_ui24(tag.timestamp & 0x00FFFFFF)
        self._writer.write_ui8(tag.timestamp >> 24)
        self._writer.write_ui24(tag.stream_id)

    def dump_audio_tag_header(self, tag: AudioTag) -> None:
        if tag.sound_format != SoundFormat.AAC:
            raise FlvDataError(f'Unsupported sound format: {tag.sound_format}', tag)
        self._writer.write_ui8(
            (tag.sound_format.value << 4)
            | (tag.sound_rate.value << 2)
            | (tag.sound_size.value << 1)
            | tag.sound_type.value
        )
        self._writer.write_ui8(tag.aac_packet_type)

    def dump_video_tag_header(self, tag: VideoTag) -> None:
        if tag.codec_id != CodecID.AVC:
            raise FlvDataError(f'Unsupported video codec: {tag.codec_id}', tag)
        self._writer.write_ui8((tag.frame_type.value << 4) | tag.codec_id.value)
        self._writer.write_ui8(tag.avc_packet_type.value)
        self._writer.write_ui24(tag.composition_time)
