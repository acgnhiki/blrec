from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, Union

import attr
from typing_extensions import TypeGuard

from . import scriptdata
from .avc import extract_resolution
from .io import FlvReader
from .io_protocols import RandomIO
from .models import (
    AudioTag,
    AVCPacketType,
    CodecID,
    FlvTag,
    FrameType,
    ScriptTag,
    TagType,
    VideoTag,
)
from .utils import OffsetRepositor


def read_tags(
    reader: FlvReader, count: int, *, no_body: bool = False
) -> Iterator[FlvTag]:
    assert count > 0, 'count must greater than 0'
    for c, tag in enumerate(reader.read_tags(no_body=no_body), start=1):
        yield tag
        if c >= count:
            break


def rread_tags(
    reader: FlvReader, count: int, *, no_body: bool = False
) -> Iterator[FlvTag]:
    assert count > 0, 'count must greater than 0'
    for c, tag in enumerate(reader.rread_tags(no_body=no_body), start=1):
        yield tag
        if c >= count:
            break


def read_tags_in_duration(
    reader: FlvReader, duration: int, *, no_body: bool = False
) -> Iterator[FlvTag]:
    for tag in reader.read_tags(no_body=no_body):
        yield tag
        if tag.timestamp > 0:
            break
    else:
        raise EOFError('no tags')

    start = tag.timestamp
    end = start + duration

    for tag in reader.read_tags(no_body=no_body):
        yield tag
        if tag.timestamp >= end:
            break


def peek_tags(
    file: RandomIO, reader: FlvReader, count: int, *, no_body: bool = False
) -> Iterator[FlvTag]:
    with OffsetRepositor(file):
        yield from read_tags(reader, count, no_body=no_body)


def rpeek_tags(
    file: RandomIO, reader: FlvReader, count: int, *, no_body: bool = False
) -> Iterator[FlvTag]:
    with OffsetRepositor(file):
        yield from rread_tags(reader, count, no_body=no_body)


def find_metadata_tag(tags: Iterable[FlvTag]) -> Optional[ScriptTag]:
    for tag in tags:
        if is_script_tag(tag):
            return tag
    return None


def find_header_tag(tags: Iterable[FlvTag]) -> Optional[Union[AudioTag, VideoTag]]:
    for tag in tags:
        if is_sequence_header(tag):
            return tag
    return None


def find_avc_header_tag(tags: Iterable[FlvTag]) -> Optional[VideoTag]:
    for tag in tags:
        if is_video_sequence_header(tag):
            return tag
    return None


def find_aac_header_tag(tags: Iterable[FlvTag]) -> Optional[AudioTag]:
    for tag in tags:
        if is_audio_sequence_header(tag):
            return tag
    return None


def find_nalu_keyframe_tag(tags: Iterable[FlvTag]) -> Optional[VideoTag]:
    for tag in tags:
        if is_video_nalu_keyframe(tag):
            return tag
    return None


def find_aac_raw_tag(tags: Iterable[FlvTag]) -> Optional[AudioTag]:
    for tag in tags:
        if is_audio_tag(tag) and tag.is_aac_raw():
            return tag
    return None


def is_audio_tag(tag: FlvTag) -> TypeGuard[AudioTag]:
    return tag.tag_type == TagType.AUDIO


def is_video_tag(tag: FlvTag) -> TypeGuard[VideoTag]:
    return tag.tag_type == TagType.VIDEO


def is_script_tag(tag: FlvTag) -> TypeGuard[ScriptTag]:
    return tag.tag_type == TagType.SCRIPT


def is_metadata_tag(tag: FlvTag) -> TypeGuard[ScriptTag]:
    if is_script_tag(tag):
        script_data = parse_scriptdata(tag)
        return script_data['name'] == 'onMetaData'
    return False


def is_data_tag(tag: FlvTag) -> TypeGuard[Union[AudioTag, VideoTag]]:
    return is_audio_data_tag(tag) or is_video_data_tag(tag)


def is_audio_data_tag(tag: FlvTag) -> TypeGuard[AudioTag]:
    return is_audio_tag(tag) and tag.is_aac_raw()


def is_video_data_tag(tag: FlvTag) -> TypeGuard[VideoTag]:
    return is_video_tag(tag) and tag.is_avc_nalu()


def is_sequence_header(tag: FlvTag) -> TypeGuard[Union[AudioTag, VideoTag]]:
    return is_audio_sequence_header(tag) or is_video_sequence_header(tag)


def is_audio_sequence_header(tag: FlvTag) -> TypeGuard[AudioTag]:
    return is_audio_tag(tag) and tag.is_aac_header()


def is_video_sequence_header(tag: FlvTag) -> TypeGuard[VideoTag]:
    return is_video_tag(tag) and tag.is_avc_header()


def is_video_nalu_keyframe(tag: FlvTag) -> TypeGuard[VideoTag]:
    return is_video_tag(tag) and tag.is_keyframe() and tag.is_avc_nalu()


def is_avc_end_sequence(tag: FlvTag) -> TypeGuard[VideoTag]:
    return is_video_tag(tag) and tag.is_avc_end()


def is_avc_end_sequence_tag(value: Any) -> TypeGuard[VideoTag]:
    return isinstance(value, FlvTag) and is_avc_end_sequence(value)


def create_avc_end_sequence_tag(offset: int = 0, timestamp: int = 0) -> VideoTag:
    return VideoTag(
        offset=offset,
        filtered=False,
        tag_type=TagType.VIDEO,
        data_size=5,
        timestamp=timestamp,
        stream_id=timestamp,
        frame_type=FrameType.KEY_FRAME,
        codec_id=CodecID.AVC,
        avc_packet_type=AVCPacketType.AVC_END_OF_SEQENCE,
        composition_time=0,
    )


def parse_scriptdata(script_tag: ScriptTag) -> scriptdata.ScriptData:
    assert script_tag.body
    return scriptdata.load(script_tag.body)


def unparse_scriptdata(
    script_tag: ScriptTag, script_data: scriptdata.ScriptData, **changes: Any
) -> ScriptTag:
    body = scriptdata.dump(script_data)
    return script_tag.evolve(body=body, **changes)


def create_script_tag(
    script_data: scriptdata.ScriptData, offset: int = 0, timestamp: int = 0
) -> ScriptTag:
    body = scriptdata.dump(script_data)
    return ScriptTag(
        filtered=False,
        tag_type=TagType.SCRIPT,
        data_size=len(body),
        timestamp=timestamp,
        stream_id=0,
        offset=offset,
        body=body,
    )


def create_metadata_tag(
    metadata: Dict[str, Any], offset: int = 0, timestamp: int = 0
) -> ScriptTag:
    script_data = scriptdata.ScriptData(name='onMetaData', value=metadata)
    return create_script_tag(script_data, offset, timestamp)


def parse_metadata(metadata_tag: ScriptTag) -> Dict[str, Any]:
    script_data = parse_scriptdata(metadata_tag)
    assert script_data['name'] == 'onMetaData'
    return script_data['value']


def unparse_metadata(
    metadata_tag: ScriptTag, metadata: Dict[str, Any], **changes: Any
) -> ScriptTag:
    script_data = scriptdata.ScriptData(name='onMetaData', value=metadata)
    return unparse_scriptdata(metadata_tag, script_data, **changes)


def enrich_metadata(
    metadata_tag: ScriptTag,
    extra_metadata: Mapping[str, Any],
    offset: Optional[int] = None,
) -> ScriptTag:
    metadata = parse_metadata(metadata_tag)
    metadata.update(extra_metadata)
    metadata = ensure_order(metadata)

    if offset is None:
        return unparse_metadata(metadata_tag, metadata)
    else:
        return unparse_metadata(metadata_tag, metadata, offset=offset)


def update_metadata(
    metadata_tag: ScriptTag, metadata: Mapping[str, Any], offset: Optional[int] = None
) -> ScriptTag:
    original_tag_size = metadata_tag.tag_size
    new_tag = enrich_metadata(metadata_tag, metadata, offset)
    assert new_tag.tag_size == original_tag_size, 'tag size must unchanged'
    return new_tag


def ensure_order(metadata: Dict[str, Any]) -> Dict[str, Any]:
    # the order of metadata property matters!!!
    # some typical properties such as 'keyframes' must be before some custom
    # properties such as 'Comment' otherwise, it won't take effect in some
    # players!
    from .operators import MetaData

    typical_props = attr.fields_dict(MetaData).keys()
    return {
        **{k: v for k, v in metadata.items() if k in typical_props},
        **{k: v for k, v in metadata.items() if k not in typical_props},
    }


@attr.s(auto_attribs=True, slots=True, frozen=True)
class Resolution:
    width: int
    height: int

    @classmethod
    def from_metadata(cls, metadata: Dict[str, Any]) -> Resolution:
        return cls(
            width=metadata.get('width') or metadata['displayWidth'],
            height=metadata.get('height') or metadata['displayHeight'],
        )

    @classmethod
    def from_avc_sequence_header(cls, tag: VideoTag) -> Resolution:
        assert tag.avc_packet_type == AVCPacketType.AVC_SEQUENCE_HEADER
        assert tag.body
        width, height = extract_resolution(tag.body)
        return cls(width, height)
