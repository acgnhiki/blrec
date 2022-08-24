import hashlib
import logging
from abc import ABC
from datetime import datetime
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlencode

import aiohttp
from tenacity import retry, stop_after_delay, wait_exponential

from .exceptions import ApiRequestError
from .typing import JsonResponse, QualityNumber, ResponseData

__all__ = 'AppApi', 'WebApi'


logger = logging.getLogger(__name__)


class BaseApi(ABC):
    base_api_url: str = 'https://api.bilibili.com'
    base_live_api_url: str = 'https://api.live.bilibili.com'
    base_play_info_api_url: str = base_live_api_url

    def __init__(
        self, session: aiohttp.ClientSession, headers: Optional[Dict[str, str]] = None
    ):
        self._session = session
        self.headers = headers or {}
        self.timeout = 10

    @property
    def headers(self) -> Dict[str, str]:
        return self._headers

    @headers.setter
    def headers(self, value: Dict[str, str]) -> None:
        self._headers = {**value}

    @staticmethod
    def _check_response(json_res: JsonResponse) -> None:
        if json_res['code'] != 0:
            raise ApiRequestError(
                json_res['code'], json_res.get('message') or json_res.get('msg') or ''
            )

    @retry(reraise=True, stop=stop_after_delay(5), wait=wait_exponential(0.1))
    async def _get_json(self, *args: Any, **kwds: Any) -> JsonResponse:
        async with self._session.get(
            *args, **kwds, timeout=self.timeout, headers=self.headers
        ) as res:
            logger.debug(f'real url: {res.real_url}')
            json_res = await res.json()
            self._check_response(json_res)
            return json_res


class AppApi(BaseApi):
    # taken from https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/other/API_sign.md  # noqa
    _appkey = '1d8b6e7d45233436'
    _appsec = '560c52ccd288fed045859ed18bffd973'

    _app_headers = {
        'User-Agent': 'Mozilla/5.0 BiliDroid/6.64.0 (bbcallen@gmail.com) os/android model/Unknown mobi_app/android build/6640400 channel/bili innerVer/6640400 osVer/6.0.1 network/2',  # noqa
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
    }

    @property
    def headers(self) -> Dict[str, str]:
        return self._headers

    @headers.setter
    def headers(self, value: Dict[str, str]) -> None:
        self._headers = {**value, **self._app_headers}

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
        url = self.base_play_info_api_url + '/xlive/app-room/v2/index/getRoomPlayInfo'
        params = self.signed(
            {
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
            }
        )
        r = await self._get_json(url, params=params, headers=self._headers)
        return r['data']

    async def get_info_by_room(self, room_id: int) -> ResponseData:
        url = self.base_live_api_url + '/xlive/app-room/v1/index/getInfoByRoom'
        params = self.signed(
            {
                'actionKey': 'appkey',
                'build': '6640400',
                'channel': 'bili',
                'device': 'android',
                'mobi_app': 'android',
                'platform': 'android',
                'room_id': room_id,
                'ts': int(datetime.utcnow().timestamp()),
            }
        )
        r = await self._get_json(url, params=params)
        return r['data']

    async def get_user_info(self, uid: int) -> ResponseData:
        url = self.base_api_url + '/x/v2/space'
        params = self.signed(
            {
                'build': '6640400',
                'channel': 'bili',
                'mobi_app': 'android',
                'platform': 'android',
                'ts': int(datetime.utcnow().timestamp()),
                'vmid': uid,
            }
        )
        r = await self._get_json(url, params=params)
        return r['data']

    async def get_danmu_info(self, room_id: int) -> ResponseData:
        url = self.base_live_api_url + '/xlive/app-room/v1/index/getDanmuInfo'
        params = self.signed(
            {
                'actionKey': 'appkey',
                'build': '6640400',
                'channel': 'bili',
                'device': 'android',
                'mobi_app': 'android',
                'platform': 'android',
                'room_id': room_id,
                'ts': int(datetime.utcnow().timestamp()),
            }
        )
        r = await self._get_json(url, params=params)
        return r['data']


class WebApi(BaseApi):
    async def room_init(self, room_id: int) -> ResponseData:
        url = self.base_live_api_url + '/room/v1/Room/room_init'
        r = await self._get_json(url, params={'id': room_id})
        return r['data']

    async def get_room_play_info(
        self, room_id: int, qn: QualityNumber = 10000
    ) -> ResponseData:
        url = self.base_play_info_api_url + '/xlive/web-room/v2/index/getRoomPlayInfo'
        params = {
            'room_id': room_id,
            'protocol': '0,1',
            'format': '0,1,2',
            'codec': '0,1',
            'qn': qn,
            'platform': 'web',
            'ptype': 8,
        }
        r = await self._get_json(url, params=params)
        return r['data']

    async def get_info_by_room(self, room_id: int) -> ResponseData:
        url = self.base_live_api_url + '/xlive/web-room/v1/index/getInfoByRoom'
        params = {'room_id': room_id}
        r = await self._get_json(url, params=params)
        return r['data']

    async def get_info(self, room_id: int) -> ResponseData:
        url = self.base_live_api_url + '/room/v1/Room/get_info'
        params = {'room_id': room_id}
        r = await self._get_json(url, params=params)
        return r['data']

    async def get_timestamp(self) -> int:
        url = self.base_live_api_url + '/av/v1/Time/getTimestamp?platform=pc'
        r = await self._get_json(url)
        return r['data']['timestamp']

    async def get_user_info(self, uid: int) -> ResponseData:
        url = self.base_api_url + '/x/space/acc/info'
        params = {'mid': uid}
        r = await self._get_json(url, params=params)
        return r['data']

    async def get_danmu_info(self, room_id: int) -> ResponseData:
        url = self.base_live_api_url + '/xlive/web-room/v1/index/getDanmuInfo'
        params = {'id': room_id}
        r = await self._get_json(url, params=params)
        return r['data']
