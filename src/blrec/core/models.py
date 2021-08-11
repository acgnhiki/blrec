import logging

import attr

from ..bili.typing import Danmaku


logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class DanmuMsg:
    mode: int
    size: int  # font size
    color: int
    date: int  # a timestamp in miliseconds
    dmid: int
    pool: int
    uid: str  # midHash
    text: str
    uname: str  # sender name

    @staticmethod
    def from_cmd(danmu: Danmaku) -> 'DanmuMsg':
        info = danmu['info']
        return DanmuMsg(
            mode=int(info[0][1]),
            size=int(info[0][2]),
            color=int(info[0][3]),
            date=int(info[0][4]),
            dmid=int(info[0][5]),
            pool=int(info[0][6]),
            uid=info[0][7],
            text=info[1],
            uname=info[2][1],
        )
