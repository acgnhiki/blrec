

import attr


@attr.s(auto_attribs=True, slots=True, frozen=True)
class Metadata:
    user_name: str
    room_id: int
    room_title: str
    area: str
    parent_area: str
    live_start_time: int  # seconds
    record_start_time: int  # seconds
    recorder: str


@attr.s(auto_attribs=True, slots=True, frozen=True)
class Danmu:
    stime: float
    mode: int
    size: int
    color: int
    date: int  # milliseconds
    pool: int
    uid: str  # uid hash
    dmid: int
    text: str
