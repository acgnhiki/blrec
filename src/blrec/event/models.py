from __future__ import annotations
from abc import ABC
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generic, TYPE_CHECKING, Type, TypeVar

import attr

if TYPE_CHECKING:
    from ..bili.models import UserInfo, RoomInfo
    from ..disk_space.space_monitor import DiskUsage


_D = TypeVar('_D', bound='BaseEventData')
_E = TypeVar('_E')
# XXX error: Invalid self argument ...
# _E = TypeVar('_E', bound='BaseEvent[BaseEventData]')


class BaseEventData(ABC):
    pass


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class BaseEvent(Generic[_D]):
    type: str
    id: uuid.UUID
    date: datetime
    data: _D

    @classmethod
    def from_data(cls: Type[_E], data: _D) -> _E:
        return cls(  # type: ignore
            id=uuid.uuid1(),
            date=datetime.now(timezone(timedelta(hours=8))),
            data=data,
        )

    def asdict(self) -> Dict[str, Any]:
        return attr.asdict(self, value_serializer=value_serializer)


def value_serializer(instance, attribute, value):  # type: ignore
    if isinstance(value, (uuid.UUID, datetime)):
        return str(value)
    return value


@attr.s(auto_attribs=True, slots=True, frozen=True)
class LiveBeganEventData(BaseEventData):
    user_info: UserInfo
    room_info: RoomInfo


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class LiveBeganEvent(BaseEvent[LiveBeganEventData]):
    type: str = 'LiveBeganEvent'
    data: LiveBeganEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class LiveEndedEventData(LiveBeganEventData):
    pass


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class LiveEndedEvent(BaseEvent[LiveEndedEventData]):
    type: str = 'LiveEndedEvent'
    data: LiveEndedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RoomChangeEventData(BaseEventData):
    room_info: RoomInfo


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class RoomChangeEvent(BaseEvent[RoomChangeEventData]):
    type: str = 'RoomChangeEvent'
    data: RoomChangeEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class SpaceNoEnoughEventData(BaseEventData):
    path: str
    threshold: int
    usage: DiskUsage


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class SpaceNoEnoughEvent(BaseEvent[SpaceNoEnoughEventData]):
    type: str = 'SpaceNoEnoughEvent'
    data: SpaceNoEnoughEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class FileCompletedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class FileCompletedEvent(BaseEvent[FileCompletedEventData]):
    type: str = 'FileCompletedEvent'
    data: FileCompletedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class ErrorData(BaseEventData):
    name: str
    detail: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class Error(BaseEvent[ErrorData]):
    type: str = 'Error'
    data: ErrorData
