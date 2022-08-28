import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List

import aiohttp
from jsonpath import jsonpath
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_exponential

from .api import AppApi, WebApi
from .exceptions import (
    LiveRoomEncrypted,
    LiveRoomHidden,
    LiveRoomLocked,
    NoAlternativeStreamAvailable,
    NoStreamAvailable,
    NoStreamCodecAvailable,
    NoStreamFormatAvailable,
    NoStreamQualityAvailable,
)
from .models import LiveStatus, RoomInfo, UserInfo
from .typing import ApiPlatform, QualityNumber, ResponseData, StreamCodec, StreamFormat

__all__ = ('Live',)

logger = logging.getLogger(__name__)

_INFO_PATTERN = re.compile(
    rb'<script>\s*window\.__NEPTUNE_IS_MY_WAIFU__\s*=\s*(\{.*?\})\s*</script>'
)
_LIVE_STATUS_PATTERN = re.compile(rb'"live_status"\s*:\s*(\d)')


class Live:
    def __init__(self, room_id: int, user_agent: str = '', cookie: str = '') -> None:
        self._room_id = room_id
        self._user_agent = user_agent
        self._cookie = cookie
        self._html_page_url = f'https://live.bilibili.com/{room_id}'

        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=200),
            raise_for_status=True,
            trust_env=True,
        )
        self._appapi = AppApi(self._session, self.headers)
        self._webapi = WebApi(self._session, self.headers)

        self._room_info: RoomInfo
        self._user_info: UserInfo

    @property
    def base_api_urls(self) -> List[str]:
        return self._webapi.base_api_urls

    @base_api_urls.setter
    def base_api_urls(self, value: List[str]) -> None:
        self._webapi.base_api_urls = value
        self._appapi.base_api_urls = value

    @property
    def base_live_api_urls(self) -> List[str]:
        return self._webapi.base_live_api_urls

    @base_live_api_urls.setter
    def base_live_api_urls(self, value: List[str]) -> None:
        self._webapi.base_live_api_urls = value
        self._appapi.base_live_api_urls = value

    @property
    def base_play_info_api_urls(self) -> List[str]:
        return self._webapi.base_play_info_api_urls

    @base_play_info_api_urls.setter
    def base_play_info_api_urls(self, value: List[str]) -> None:
        self._webapi.base_play_info_api_urls = value
        self._appapi.base_play_info_api_urls = value

    @property
    def user_agent(self) -> str:
        return self._user_agent

    @user_agent.setter
    def user_agent(self, value: str) -> None:
        self._user_agent = value
        self._webapi.headers = self.headers
        self._appapi.headers = self.headers

    @property
    def cookie(self) -> str:
        return self._cookie

    @cookie.setter
    def cookie(self, value: str) -> None:
        self._cookie = value
        self._webapi.headers = self.headers
        self._appapi.headers = self.headers

    @property
    def headers(self) -> Dict[str, str]:
        return {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en;q=0.3,en-US;q=0.2',  # noqa
            'Referer': f'https://live.bilibili.com/{self._room_id}',
            'Origin': 'https://live.bilibili.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'User-Agent': self._user_agent,
            'Cookie': self._cookie,
            'Accept-Encoding': 'gzip',
        }

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def appapi(self) -> AppApi:
        return self._appapi

    @property
    def webapi(self) -> WebApi:
        return self._webapi

    @property
    def room_id(self) -> int:
        return self._room_id

    @property
    def room_info(self) -> RoomInfo:
        return self._room_info

    @property
    def user_info(self) -> UserInfo:
        return self._user_info

    async def init(self) -> None:
        self._room_info = await self.get_room_info()
        self._user_info = await self.get_user_info(self._room_info.uid)

    async def deinit(self) -> None:
        await self._session.close()

    async def get_live_status(self) -> LiveStatus:
        try:
            # frequent requests will be intercepted by the server's firewall!
            live_status = await self._get_live_status_via_api()
        except Exception:
            # more cpu consumption
            live_status = await self._get_live_status_via_html_page()

        return LiveStatus(live_status)

    def is_living(self) -> bool:
        return self._room_info.live_status == LiveStatus.LIVE

    async def check_connectivity(self) -> bool:
        try:
            await self._session.head('https://live.bilibili.com/', timeout=3)
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            return False
        else:
            return True

    async def update_info(self, raise_exception: bool = False) -> bool:
        return all(
            await asyncio.gather(
                self.update_user_info(raise_exception=raise_exception),
                self.update_room_info(raise_exception=raise_exception),
            )
        )

    async def update_user_info(self, raise_exception: bool = False) -> bool:
        try:
            self._user_info = await self.get_user_info(self._room_info.uid)
        except Exception as e:
            logger.error(f'Failed to update user info: {repr(e)}')
            if raise_exception:
                raise
            return False
        else:
            return True

    async def update_room_info(self, raise_exception: bool = False) -> bool:
        try:
            self._room_info = await self.get_room_info()
        except Exception as e:
            logger.error(f'Failed to update room info: {repr(e)}')
            if raise_exception:
                raise
            return False
        else:
            return True

    @retry(
        retry=retry_if_exception_type(
            (asyncio.TimeoutError, aiohttp.ClientError, ValueError)
        ),
        wait=wait_exponential(max=10),
        stop=stop_after_delay(60),
    )
    async def get_room_info(self) -> RoomInfo:
        try:
            # frequent requests will be intercepted by the server's firewall!
            room_info_data = await self._get_room_info_via_api()
        except Exception:
            # more cpu consumption
            room_info_data = await self._get_room_info_via_html_page()
        return RoomInfo.from_data(room_info_data)

    @retry(
        retry=retry_if_exception_type((asyncio.TimeoutError, aiohttp.ClientError)),
        wait=wait_exponential(max=10),
        stop=stop_after_delay(60),
    )
    async def get_user_info(self, uid: int) -> UserInfo:
        try:
            user_info_data = await self._webapi.get_user_info(uid)
            return UserInfo.from_web_api_data(user_info_data)
        except Exception:
            user_info_data = await self._appapi.get_user_info(uid)
            return UserInfo.from_app_api_data(user_info_data)

    async def get_timestamp(self) -> int:
        try:
            ts = await self.get_server_timestamp()
        except Exception as e:
            logger.warning(f'Failed to get timestamp from server: {repr(e)}')
            ts = int(time.time())
        return ts

    async def get_server_timestamp(self) -> int:
        # the timestamp on the server at the moment in seconds
        return await self._webapi.get_timestamp()

    async def get_live_stream_url(
        self,
        qn: QualityNumber = 10000,
        *,
        api_platform: ApiPlatform = 'web',
        stream_format: StreamFormat = 'flv',
        stream_codec: StreamCodec = 'avc',
        select_alternative: bool = False,
    ) -> str:
        if api_platform == 'web':
            paly_infos = await self._webapi.get_room_play_infos(self._room_id, qn)
        else:
            paly_infos = await self._appapi.get_room_play_infos(self._room_id, qn)

        for info in paly_infos:
            self._check_room_play_info(info)

        streams = jsonpath(paly_infos, '$[*].playurl_info.playurl.stream[*]')
        if not streams:
            raise NoStreamAvailable(stream_format, stream_codec, qn)
        formats = jsonpath(
            streams, f'$[*].format[?(@.format_name == "{stream_format}")]'
        )
        if not formats:
            raise NoStreamFormatAvailable(stream_format, stream_codec, qn)
        codecs = jsonpath(formats, f'$[*].codec[?(@.codec_name == "{stream_codec}")]')
        if not codecs:
            raise NoStreamCodecAvailable(stream_format, stream_codec, qn)

        accept_qns = jsonpath(codecs, '$[*].accept_qn[*]')
        current_qns = jsonpath(codecs, '$[*].current_qn')
        if qn not in accept_qns or not all(map(lambda q: q == qn, current_qns)):
            raise NoStreamQualityAvailable(stream_format, stream_codec, qn)

        def sort_by_host(info: Any) -> int:
            host = info['host']
            if match := re.search(r'gotcha(\d+)', host):
                num = match.group(1)
                if num == '04':
                    return 0
                if num == '09':
                    return 1
                if num == '08':
                    return 2
                if num == '05':
                    return 3
                if num == '07':
                    return 4
                return 1000 + int(num)
            elif 'mcdn' in host:
                return 2000
            elif re.search(r'cn-[a-z]+-[a-z]+', host):
                return 5000
            else:
                return 10000

        url_infos = sorted(
            ({**i, 'base_url': c['base_url']} for c in codecs for i in c['url_info']),
            key=sort_by_host,
        )
        urls = [i['host'] + i['base_url'] + i['extra'] for i in url_infos]

        if not select_alternative:
            return urls[0]

        try:
            return urls[1]
        except IndexError:
            raise NoAlternativeStreamAvailable(stream_format, stream_codec, qn)

    def _check_room_play_info(self, data: ResponseData) -> None:
        if data.get('is_hidden'):
            raise LiveRoomHidden()
        if data.get('is_locked'):
            raise LiveRoomLocked()
        if data.get('encrypted') and not data.get('pwd_verified'):
            raise LiveRoomEncrypted()

    async def _get_live_status_via_api(self) -> int:
        room_info_data = await self._get_room_info_via_api()
        return int(room_info_data['live_status'])

    async def _get_room_info_via_api(self) -> ResponseData:
        try:
            info_data = await self._webapi.get_info_by_room(self._room_id)
            room_info_data = info_data['room_info']
        except Exception:
            try:
                info_data = await self._appapi.get_info_by_room(self._room_id)
                room_info_data = info_data['room_info']
            except Exception:
                room_info_data = await self._webapi.get_info(self._room_id)

        return room_info_data

    async def _get_live_status_via_html_page(self) -> int:
        async with self._session.get(self._html_page_url) as response:
            data = await response.read()

        m = _LIVE_STATUS_PATTERN.search(data)
        assert m is not None, data

        return int(m.group(1))

    async def _get_room_info_via_html_page(self) -> ResponseData:
        info_res = await self._get_room_info_res_via_html_page()
        return info_res['room_info']

    async def _get_room_play_info_via_html_page(self) -> ResponseData:
        return await self._get_room_init_res_via_html_page()

    async def _get_room_info_res_via_html_page(self) -> ResponseData:
        info = await self._get_info_via_html_page()
        if info['roomInfoRes']['code'] != 0:
            raise ValueError(f"Invaild roomInfoRes: {info['roomInfoRes']}")
        return info['roomInfoRes']['data']

    async def _get_room_init_res_via_html_page(self) -> ResponseData:
        info = await self._get_info_via_html_page()
        if info['roomInitRes']['code'] != 0:
            raise ValueError(f"Invaild roomInitRes: {info['roomInitRes']}")
        return info['roomInitRes']['data']

    async def _get_info_via_html_page(self) -> ResponseData:
        async with self._session.get(self._html_page_url) as response:
            data = await response.read()

        match = _INFO_PATTERN.search(data)
        if not match:
            raise ValueError('Can not extract info from html page')

        string = match.group(1).decode(encoding='utf8')
        return json.loads(string)
