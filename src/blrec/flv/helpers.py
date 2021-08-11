import json
from typing import Any, Dict, Iterable


from .io import FlvReader
from .common import (
    is_audio_tag, is_metadata_tag, is_script_tag, is_video_tag, read_tags,
    parse_metadata, find_metadata_tag,
)
from .stream_processor import JoinPoint
from .utils import format_timestamp
from ..path import extra_metadata_path


def get_metadata(path: str) -> Dict[str, Any]:
    with open(path, mode='rb') as file:
        reader = FlvReader(file)
        reader.read_header()
        if (tag := find_metadata_tag(reversed(list(read_tags(reader, 5))))):
            return parse_metadata(tag)
        raise EOFError


def get_extra_metadata(flv_path: str) -> Dict[str, Any]:
    path = extra_metadata_path(flv_path)
    with open(path, 'rt', encoding='utf8') as file:
        return json.load(file)


def make_comment_for_joinpoints(join_points: Iterable[JoinPoint]) -> str:
    return (
        '流中断拼接详情\n' +
        '\n'.join((
            '时间戳：{}, 无缝拼接：{}'.format(
                format_timestamp(p.timestamp),
                '是' if p.seamless else '否',
            )
            for p in join_points
        ))
    )


def is_valid(path: str) -> bool:
    with open(path, mode='rb') as file:
        reader = FlvReader(file)

        try:
            flv_header = reader.read_header()
        except EOFError:
            return False

        MAX_TAGS_TO_FIND = 50
        has_metadata_tag = False
        has_audio_header_tag = False
        has_audio_data_tag = False
        has_video_header_tag = False
        has_video_data_tag = False

        for tag in read_tags(reader, MAX_TAGS_TO_FIND, no_body=True):
            if is_script_tag(tag):
                tag = tag.evolve(body=reader.read_body(tag))
                if is_metadata_tag(tag):
                    has_metadata_tag = True
            elif is_audio_tag(tag):
                if tag.is_aac_header():
                    has_audio_header_tag = True
                elif tag.is_aac_raw():
                    has_audio_data_tag = True
            elif is_video_tag(tag):
                if tag.is_avc_header():
                    has_video_header_tag = True
                elif tag.is_avc_nalu():
                    has_video_data_tag = True
            else:
                pass

            if (
                has_metadata_tag and (
                    flv_header.has_video() ==
                    has_video_header_tag ==
                    has_video_data_tag
                ) and (
                    flv_header.has_audio() ==
                    has_audio_header_tag ==
                    has_audio_data_tag
                )
            ):
                return True

        return False
