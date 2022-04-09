
import aiohttp

from .api import WebApi
from .typing import ResponseData, QualityNumber
from .exceptions import ApiRequestError
from ..exception import NotFoundError


__all__ = 'room_init', 'ensure_room_id'


async def room_init(room_id: int) -> ResponseData:
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        api = WebApi(session)
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
