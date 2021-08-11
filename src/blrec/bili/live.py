
import asyncio
import re
import json
from typing import Dict, List, Optional, cast

import aiohttp

from .api import WebApi
from .models import LiveStatus, RoomInfo, UserInfo
from .typing import QualityNumber, StreamFormat, ResponseData
from .exceptions import (
    LiveRoomHidden, LiveRoomLocked, LiveRoomEncrypted, NoStreamUrlAvailable
)


__all__ = 'Live',


_INFO_PATTERN = re.compile(
    rb'<script>\s*window\.__NEPTUNE_IS_MY_WAIFU__\s*=\s*(\{.*?\})\s*</script>'
)
_LIVE_STATUS_PATTERN = re.compile(rb'"live_status"\s*:\s*(\d)')


class Live:
    def __init__(
        self, room_id: int, user_agent: str = '', cookie: str = ''
    ) -> None:
        self._room_id = room_id
        self._user_agent = user_agent
        self._cookie = cookie
        self._html_page_url = f'https://live.bilibili.com/{room_id}'

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
            'User-Agent': self._user_agent,
            'cookie': self._cookie,
        }

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

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
            headers=self.headers,
            raise_for_status=True,
            trust_env=True,
        )
        self._api = WebApi(self._session)

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

    async def update_info(self) -> None:
        await asyncio.wait([self.update_user_info(), self.update_room_info()])

    async def update_user_info(self) -> None:
        self._user_info = await self.get_user_info(self._room_info.uid)

    async def update_room_info(self) -> None:
        self._room_info = await self.get_room_info()

    async def get_room_info(self) -> RoomInfo:
        try:
            # frequent requests will be intercepted by the server's firewall!
            room_info_data = await self._get_room_info_via_api()
        except Exception:
            # more cpu consumption
            room_info_data = await self._get_room_info_via_html_page()

        return RoomInfo.from_data(room_info_data)

    async def get_user_info(self, uid: int) -> UserInfo:
        user_info_data = await self._api.get_user_info(uid)
        return UserInfo.from_data(user_info_data)

    async def get_server_timestamp(self) -> int:
        # the timestamp on the server at the moment in seconds
        return await self._api.get_timestamp()

    async def get_live_stream_url(
        self, qn: QualityNumber = 10000, format: StreamFormat = 'flv'
    ) -> Optional[str]:
        try:
            data = await self._api.get_room_play_info(self._room_id, qn)
        except Exception:
            # fallback to the html page global info
            data = await self._get_room_play_info_via_html_page()
            self._check_room_play_info(data)
            stream = data['playurl_info']['playurl']['stream']
            if stream[0]['format'][0]['codec'][0]['current_qn'] != qn:
                raise
        else:
            self._check_room_play_info(data)

        streams = list(filter(
            lambda s: s['format'][0]['format_name'] == format,
            data['playurl_info']['playurl']['stream']
        ))
        codec = streams[0]['format'][0]['codec'][0]
        accept_qn = cast(List[QualityNumber], codec['accept_qn'])

        if qn not in accept_qn:
            return None

        assert codec['current_qn'] == qn
        url_info = codec['url_info'][0]

        return url_info['host'] + codec['base_url'] + url_info['extra']

    def _check_room_play_info(self, data: ResponseData) -> None:
        if data['is_hidden']:
            raise LiveRoomHidden()
        if data['is_locked']:
            raise LiveRoomLocked()
        if data['encrypted'] and not data['pwd_verified']:
            raise LiveRoomEncrypted()
        try:
            data['playurl_info']['playurl']['stream'][0]
        except Exception:
            raise NoStreamUrlAvailable()

    async def _get_live_status_via_api(self) -> int:
        room_info_data = await self._get_room_info_via_api()
        return int(room_info_data['live_status'])

    async def _get_room_info_via_api(self) -> ResponseData:
        try:
            room_info_data = await self._api.get_info(self._room_id)
        except Exception:
            info_data = await self._api.get_info_by_room(self._room_id)
            room_info_data = info_data['room_info']

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

        m = _INFO_PATTERN.search(data)
        assert m is not None, data

        string = m.group(1).decode(encoding='utf8')
        return json.loads(string)
