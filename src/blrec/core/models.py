from typing import Literal

import attr

from blrec.bili.typing import Danmaku


@attr.s(auto_attribs=True, frozen=True, slots=True)
class DanmuMsg:
    mode: int
    size: int  # font size
    color: int
    date: int  # a timestamp in miliseconds
    dmid: int
    pool: int
    uid_hash: str
    uid: int
    uname: str  # sender name
    text: str

    @staticmethod
    def from_danmu(danmu: Danmaku) -> 'DanmuMsg':
        info = danmu['info']
        return DanmuMsg(
            mode=int(info[0][1]),
            size=int(info[0][2]),
            color=int(info[0][3]),
            date=int(info[0][4]),
            dmid=int(info[0][5]),
            pool=int(info[0][6]),
            uid_hash=info[0][7],
            uid=int(info[2][0]),
            uname=info[2][1],
            text=info[1],
        )


@attr.s(auto_attribs=True, slots=True, frozen=True)
class UserToastMsg:
    start_time: int  # timestamp in seconds
    uid: int
    username: str
    unit: str
    num: int
    price: int
    role_name: str
    guard_level: str
    toast_msg: str

    @staticmethod
    def from_danmu(danmu: Danmaku) -> 'UserToastMsg':
        data = danmu['data']
        return UserToastMsg(
            start_time=data['start_time'],
            uid=data['uid'],
            username=data['username'],
            unit=data['unit'],
            num=data['num'],
            price=data['price'],
            role_name=data['role_name'],
            guard_level=data['guard_level'],
            toast_msg=data['toast_msg'].replace('<%', '').replace('%>', ''),
        )


@attr.s(auto_attribs=True, frozen=True, slots=True)
class GiftSendMsg:
    gift_name: str
    count: int
    coin_type: Literal['sliver', 'gold']
    price: int
    uid: int
    uname: str
    timestamp: int  # timestamp in seconds

    @staticmethod
    def from_danmu(danmu: Danmaku) -> 'GiftSendMsg':
        data = danmu['data']
        return GiftSendMsg(
            gift_name=data['giftName'],
            count=int(data['num']),
            coin_type=data['coin_type'],
            price=int(data['price']),
            uid=int(data['uid']),
            uname=data['uname'],
            timestamp=int(data['timestamp']),
        )


@attr.s(auto_attribs=True, frozen=True, slots=True)
class GuardBuyMsg:
    gift_name: str
    count: int
    price: int
    uid: int
    uname: str
    guard_level: int  # 1 总督, 2 提督, 3 舰长
    timestamp: int  # timestamp in seconds

    @staticmethod
    def from_danmu(danmu: Danmaku) -> 'GuardBuyMsg':
        data = danmu['data']
        return GuardBuyMsg(
            gift_name=data['gift_name'],
            count=int(data['num']),
            price=int(data['price']),
            uid=int(data['uid']),
            uname=data['username'],
            guard_level=int(data['guard_level']),
            timestamp=int(data['start_time']),
        )


@attr.s(auto_attribs=True, frozen=True, slots=True)
class SuperChatMsg:
    gift_name: str
    count: int
    price: int
    rate: int
    time: int  # duration in seconds
    message: str
    uid: int
    uname: str
    timestamp: int  # timestamp in seconds

    @staticmethod
    def from_danmu(danmu: Danmaku) -> 'SuperChatMsg':
        data = danmu['data']
        return SuperChatMsg(
            gift_name=data['gift']['gift_name'],
            count=int(data['gift']['num']),
            price=int(data['price']),
            rate=int(data['rate']),
            time=int(data['time']),
            message=data['message'],
            uid=int(data['uid']),
            uname=data['user_info']['uname'],
            timestamp=int(data['ts']),
        )
