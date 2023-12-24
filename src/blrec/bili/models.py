import re
from enum import IntEnum
from datetime import datetime
from typing import cast

import attr
from lxml import html
from lxml.html.clean import clean_html

from .typing import ResponseData
from ..utils.url import ensure_scheme


__all__ = 'LiveStatus', 'RoomInfo', 'UserInfo'


class LiveStatus(IntEnum):
    PREPARING = 0
    LIVE = 1
    ROUND = 2


@attr.s(auto_attribs=True, frozen=True, slots=True)
class RoomInfo:
    uid: int
    room_id: int
    short_room_id: int
    area_id: int
    area_name: str
    parent_area_id: int
    parent_area_name: str
    live_status: LiveStatus
    live_start_time: int  # a integer in seconds
    online: int
    title: str
    cover: str
    tags: str
    description: str

    @staticmethod
    def from_data(data: ResponseData) -> 'RoomInfo':
        if (timestamp := data.get('live_start_time')) is not None:
            live_start_time = cast(int, timestamp)
        elif (time_string := data.get('live_time')) is not None:
            if time_string == '0000-00-00 00:00:00':
                live_start_time = 0
            else:
                dt = datetime.fromisoformat(time_string)
                live_start_time = int(dt.timestamp())
        else:
            raise ValueError(f'Failed to init live_start_time: {data}')

        if cover := data.get('cover') or data.get('user_cover', ''):
            cover = ensure_scheme(cover, 'https')

        if description := data['description']:
            description = re.sub(r'<br\s*/?>', '\n', description)
            tree = html.fromstring(description)
            description = clean_html(tree).text_content().strip()

        return RoomInfo(
            uid=data['uid'],
            room_id=int(data['room_id']),
            short_room_id=int(data['short_id']),
            area_id=data['area_id'],
            area_name=data['area_name'],
            parent_area_id=data['parent_area_id'],
            parent_area_name=data['parent_area_name'],
            live_status=LiveStatus(data['live_status']),
            live_start_time=live_start_time,
            online=int(data['online']),
            title=data['title'],
            cover=cover,
            tags=data['tags'],
            description=description,
        )


@attr.s(auto_attribs=True, frozen=True, slots=True)
class UserInfo:
    name: str
    gender: str
    face: str
    uid: int

    @staticmethod
    def from_web_api_data(data: ResponseData) -> 'UserInfo':
        return UserInfo(
            name=data['name'],
            gender=data['sex'],
            face=ensure_scheme(data['face'], 'https'),
            uid=data['mid'],
        )

    @staticmethod
    def from_app_api_data(data: ResponseData) -> 'UserInfo':
        card = data['card']
        return UserInfo(
            name=card['name'],
            gender=card.get('sex', ''),
            face=ensure_scheme(card['face'], 'https'),
            uid=card['mid'],
        )

    @staticmethod
    def from_info_by_room(data: ResponseData) -> 'UserInfo':
        room_info = data['room_info']
        base_info = data['anchor_info']['base_info']
        return UserInfo(
            name=base_info['uname'],
            gender=base_info['gender'],
            face=ensure_scheme(base_info['face'], 'https'),
            uid=room_info['uid'],
        )
