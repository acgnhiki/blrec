from typing import Any, Final

import aiohttp
from tenacity import (
    retry,
    wait_exponential,
    stop_after_delay,
)

from .typing import QualityNumber, JsonResponse, ResponseData
from .exceptions import ApiRequestError


__all__ = 'WebApi',


class WebApi:
    BASE_API_URL: Final[str] = 'https://api.bilibili.com'
    BASE_LIVE_API_URL: Final[str] = 'https://api.live.bilibili.com'

    GET_USER_INFO_URL: Final[str] = BASE_API_URL + '/x/space/acc/info'

    ROOM_INIT_URL: Final[str] = BASE_LIVE_API_URL + '/room/v1/Room/room_init'
    GET_INFO_URL: Final[str] = BASE_LIVE_API_URL + '/room/v1/Room/get_info'
    GET_INFO_BY_ROOM_URL: Final[str] = BASE_LIVE_API_URL + \
        '/xlive/web-room/v1/index/getInfoByRoom'
    GET_ROOM_PLAY_INFO_URL: Final[str] = BASE_LIVE_API_URL + \
        '/xlive/web-room/v2/index/getRoomPlayInfo'
    GET_TIMESTAMP_URL: Final[str] = BASE_LIVE_API_URL + \
        '/av/v1/Time/getTimestamp?platform=pc'

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session
        self.timeout = 10

    @staticmethod
    def _check_response(json_res: JsonResponse) -> None:
        if json_res['code'] != 0:
            raise ApiRequestError(
                json_res['code'],
                json_res.get('message') or json_res.get('msg') or '',
            )

    @retry(
        reraise=True,
        stop=stop_after_delay(5),
        wait=wait_exponential(0.1),
    )
    async def _get(self, *args: Any, **kwds: Any) -> JsonResponse:
        async with self._session.get(
            *args,
            **kwds,
            timeout=self.timeout,
        ) as res:
            json_res = await res.json()
            self._check_response(json_res)
            return json_res

    async def room_init(self, room_id: int) -> ResponseData:
        r = await self._get(self.ROOM_INIT_URL, params={'id': room_id})
        return r['data']

    async def get_room_play_info(
        self, room_id: int, qn: QualityNumber = 10000
    ) -> ResponseData:
        params = {
            'room_id': room_id,
            'protocol': '0,1',
            'format': '0,2',
            'codec': '0,1',
            'qn': qn,
            'platform': 'web',
            'ptype': 16,
        }
        r = await self._get(self.GET_ROOM_PLAY_INFO_URL, params=params)
        return r['data']

    async def get_info_by_room(self, room_id: int) -> ResponseData:
        params = {
            'room_id': room_id,
        }
        r = await self._get(self.GET_INFO_BY_ROOM_URL, params=params)
        return r['data']

    async def get_info(self, room_id: int) -> ResponseData:
        params = {
            'room_id': room_id,
        }
        r = await self._get(self.GET_INFO_URL, params=params)
        return r['data']

    async def get_timestamp(self) -> int:
        r = await self._get(self.GET_TIMESTAMP_URL)
        return r['data']['timestamp']

    async def get_user_info(self, uid: int) -> ResponseData:
        params = {
            'mid': uid,
        }
        r = await self._get(self.GET_USER_INFO_URL, params=params)
        return r['data']
