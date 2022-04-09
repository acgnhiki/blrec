from abc import ABC
import hashlib
from urllib.parse import urlencode
from datetime import datetime
from typing import Mapping, Dict, Any, Final

import aiohttp
from tenacity import (
    retry,
    wait_exponential,
    stop_after_delay,
)

from .typing import QualityNumber, JsonResponse, ResponseData
from .exceptions import ApiRequestError


__all__ = 'AppApi', 'WebApi'


class BaseApi(ABC):
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


class AppApi(BaseApi):
    # taken from https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/other/API_sign.md  # noqa
    _appkey = '1d8b6e7d45233436'
    _appsec = '560c52ccd288fed045859ed18bffd973'

    _headers = {
        'User-Agent': 'Mozilla/5.0 BiliDroid/6.64.0 (bbcallen@gmail.com) os/android model/Unknown mobi_app/android build/6640400 channel/bili innerVer/6640400 osVer/6.0.1 network/2',  # noqa
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
    }

    @classmethod
    def signed(cls, params: Mapping[str, Any]) -> Dict[str, Any]:
        if isinstance(params, Mapping):
            params = dict(sorted({**params, 'appkey': cls._appkey}.items()))
        else:
            raise ValueError(type(params))
        query = urlencode(params, doseq=True)
        sign = hashlib.md5((query + cls._appsec).encode()).hexdigest()
        params.update(sign=sign)
        return params

    async def get_room_play_info(
        self,
        room_id: int,
        qn: QualityNumber = 10000,
        *,
        only_video: bool = False,
        only_audio: bool = False,
    ) -> ResponseData:
        url = 'https://api.live.bilibili.com/xlive/app-room/v2/index/getRoomPlayInfo'  # noqa

        params = self.signed({
            'actionKey': 'appkey',
            'build': '6640400',
            'channel': 'bili',
            'codec': '0,1',  # 0: avc, 1: hevc
            'device': 'android',
            'device_name': 'Unknown',
            'disable_rcmd': '0',
            'dolby': '1',
            'format': '0,1,2',  # 0: flv, 1: ts, 2: fmp4
            'free_type': '0',
            'http': '1',
            'mask': '0',
            'mobi_app': 'android',
            'need_hdr': '0',
            'no_playurl': '0',
            'only_audio': '1' if only_audio else '0',
            'only_video': '1' if only_video else '0',
            'platform': 'android',
            'play_type': '0',
            'protocol': '0,1',
            'qn': qn,
            'room_id': room_id,
            'ts': int(datetime.utcnow().timestamp()),
        })

        r = await self._get(url, params=params, headers=self._headers)
        return r['data']

    async def get_info_by_room(self, room_id: int) -> ResponseData:
        url = 'https://api.live.bilibili.com/xlive/app-room/v1/index/getInfoByRoom'  # noqa

        params = self.signed({
            'actionKey': 'appkey',
            'build': '6640400',
            'channel': 'bili',
            'device': 'android',
            'mobi_app': 'android',
            'platform': 'android',
            'room_id': room_id,
            'ts': int(datetime.utcnow().timestamp()),
        })

        r = await self._get(url, params=params)
        return r['data']

    async def get_user_info(self, uid: int) -> ResponseData:
        url = 'https://app.bilibili.com/x/v2/space'

        params = self.signed({
            'build': '6640400',
            'channel': 'bili',
            'mobi_app': 'android',
            'platform': 'android',
            'ts': int(datetime.utcnow().timestamp()),
            'vmid': uid,
        })

        r = await self._get(url, params=params)
        return r['data']

    async def get_danmu_info(self, room_id: int) -> ResponseData:
        url = 'https://api.live.bilibili.com/xlive/app-room/v1/index/getDanmuInfo'  # noqa

        params = self.signed({
            'actionKey': 'appkey',
            'build': '6640400',
            'channel': 'bili',
            'device': 'android',
            'mobi_app': 'android',
            'platform': 'android',
            'room_id': room_id,
            'ts': int(datetime.utcnow().timestamp()),
        })

        r = await self._get(url, params=params)
        return r['data']


class WebApi(BaseApi):
    BASE_API_URL: Final[str] = 'https://api.bilibili.com'
    BASE_LIVE_API_URL: Final[str] = 'https://api.live.bilibili.com'

    GET_USER_INFO_URL: Final[str] = BASE_API_URL + '/x/space/acc/info'

    GET_DANMU_INFO_URL: Final[str] = BASE_LIVE_API_URL + \
        '/xlive/web-room/v1/index/getDanmuInfo'
    ROOM_INIT_URL: Final[str] = BASE_LIVE_API_URL + '/room/v1/Room/room_init'
    GET_INFO_URL: Final[str] = BASE_LIVE_API_URL + '/room/v1/Room/get_info'
    GET_INFO_BY_ROOM_URL: Final[str] = BASE_LIVE_API_URL + \
        '/xlive/web-room/v1/index/getInfoByRoom'
    GET_ROOM_PLAY_INFO_URL: Final[str] = BASE_LIVE_API_URL + \
        '/xlive/web-room/v2/index/getRoomPlayInfo'
    GET_TIMESTAMP_URL: Final[str] = BASE_LIVE_API_URL + \
        '/av/v1/Time/getTimestamp?platform=pc'

    async def room_init(self, room_id: int) -> ResponseData:
        r = await self._get(self.ROOM_INIT_URL, params={'id': room_id})
        return r['data']

    async def get_room_play_info(
        self, room_id: int, qn: QualityNumber = 10000
    ) -> ResponseData:
        params = {
            'room_id': room_id,
            'protocol': '0,1',
            'format': '0,1,2',
            'codec': '0,1',
            'qn': qn,
            'platform': 'web',
            'ptype': 8,
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

    async def get_danmu_info(self, room_id: int) -> ResponseData:
        params = {
            'id': room_id,
        }
        r = await self._get(self.GET_DANMU_INFO_URL, params=params)
        return r['data']
