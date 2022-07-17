import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, cast

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

        self._room_info: RoomInfo
        self._user_info: UserInfo

    @property
    def user_agent(self) -> str:
        return self._user_agent

    @user_agent.setter
    def user_agent(self, value: str) -> None:
        self._user_agent = value

    @property
    def cookie(self) -> str:
        return self._cookie

    @cookie.setter
    def cookie(self, value: str) -> None:
        self._cookie = value

    @property
    def headers(self) -> Dict[str, str]:
        return {
            'Referer': 'https://live.bilibili.com/',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'User-Agent': self._user_agent,
            'Cookie': self._cookie,
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
        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=200),
            headers=self.headers,
            raise_for_status=True,
            trust_env=True,
        )
        self._appapi = AppApi(self._session)
        self._webapi = WebApi(self._session)

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
            info = await self._webapi.get_room_play_info(self._room_id, qn)
        else:
            info = await self._appapi.get_room_play_info(self._room_id, qn)

        self._check_room_play_info(info)

        streams = jsonpath(info, '$.playurl_info.playurl.stream[*]')
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
        codec = codecs[0]

        accept_qn = cast(List[QualityNumber], codec['accept_qn'])
        if qn not in accept_qn or codec['current_qn'] != qn:
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
                return int(num)
            elif re.search(r'cn-[a-z]+-[a-z]+', host):
                return 1000
            elif 'mcdn' in host:
                return 2000
            else:
                return 10000

        url_info = sorted(codec['url_info'], key=sort_by_host)
        urls = [i['host'] + codec['base_url'] + i['extra'] for i in url_info]

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
