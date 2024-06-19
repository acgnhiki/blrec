from typing import Any, Dict, List

import aiohttp
from jsonpath import jsonpath

from ..exception import NotFoundError
from .api import WebApi
from .exceptions import ApiRequestError
from .net import connector, timeout
from .typing import QualityNumber, ResponseData, StreamCodec, StreamFormat

__all__ = 'room_init', 'ensure_room_id'


async def room_init(room_id: int) -> ResponseData:
    async with aiohttp.ClientSession(
        connector=connector,
        connector_owner=False,
        raise_for_status=True,
        trust_env=True,
        timeout=timeout,
    ) as session:
        api = WebApi(session, room_id=room_id)
        return await api.room_init(room_id)


async def ensure_room_id(room_id: int) -> int:
    """Ensure room id is valid and is the real room id"""
    try:
        result = await room_init(room_id)
    except ApiRequestError as e:
        if e.code == 60004:
            raise NotFoundError(f'the room {room_id} not existed')
        else:
            raise
    else:
        return result['room_id']


async def get_nav(cookie: str) -> ResponseData:
    async with aiohttp.ClientSession(
        connector=connector,
        connector_owner=False,
        raise_for_status=True,
        trust_env=True,
        timeout=timeout,
    ) as session:
        headers = {
            'Origin': 'https://passport.bilibili.com',
            'Referer': 'https://passport.bilibili.com/account/security',
            'Cookie': cookie,
        }
        api = WebApi(session, headers)
        return await api.get_nav()


def get_quality_name(qn: QualityNumber) -> str:
    QUALITY_MAPPING = {
        20000: '4K',
        10000: '原画',
        401: '蓝光(杜比)',
        400: '蓝光',
        250: '超清',
        150: '高清',
        80: '流畅',
    }
    return QUALITY_MAPPING.get(qn, '')


def extract_streams(play_infos: List[Dict[str, Any]]) -> List[Any]:
    streams = jsonpath(play_infos, '$[*].playurl_info.playurl.stream[*]')
    return streams


def extract_formats(streams: List[Any], stream_format: StreamFormat) -> List[Any]:
    formats = jsonpath(streams, f'$[*].format[?(@.format_name == "{stream_format}")]')
    return formats


def extract_codecs(formats: List[Any], stream_codec: StreamCodec) -> List[Any]:
    codecs = jsonpath(formats, f'$[*].codec[?(@.codec_name == "{stream_codec}")]')
    return codecs
