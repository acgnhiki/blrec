from __future__ import annotations

import uuid
from abc import ABC
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Type, TypeVar

import attr

if TYPE_CHECKING:
    from ..bili.models import UserInfo, RoomInfo
    from ..disk_space.space_monitor import DiskUsage

from ..exception import format_exception

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
            id=uuid.uuid1(), date=datetime.now(timezone(timedelta(hours=8))), data=data
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
class RecordingStartedEventData(BaseEventData):
    room_info: RoomInfo


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class RecordingStartedEvent(BaseEvent[RecordingStartedEventData]):
    type: str = 'RecordingStartedEvent'
    data: RecordingStartedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RecordingFinishedEventData(BaseEventData):
    room_info: RoomInfo


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class RecordingFinishedEvent(BaseEvent[RecordingFinishedEventData]):
    type: str = 'RecordingFinishedEvent'
    data: RecordingFinishedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RecordingCancelledEventData(BaseEventData):
    room_info: RoomInfo


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class RecordingCancelledEvent(BaseEvent[RecordingCancelledEventData]):
    type: str = 'RecordingCancelledEvent'
    data: RecordingCancelledEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class VideoFileCreatedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class VideoFileCreatedEvent(BaseEvent[VideoFileCreatedEventData]):
    type: str = 'VideoFileCreatedEvent'
    data: VideoFileCreatedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class VideoFileCompletedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class VideoFileCompletedEvent(BaseEvent[VideoFileCompletedEventData]):
    type: str = 'VideoFileCompletedEvent'
    data: VideoFileCompletedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class DanmakuFileCreatedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class DanmakuFileCreatedEvent(BaseEvent[DanmakuFileCreatedEventData]):
    type: str = 'DanmakuFileCreatedEvent'
    data: DanmakuFileCreatedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class DanmakuFileCompletedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class DanmakuFileCompletedEvent(BaseEvent[DanmakuFileCompletedEventData]):
    type: str = 'DanmakuFileCompletedEvent'
    data: DanmakuFileCompletedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RawDanmakuFileCreatedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class RawDanmakuFileCreatedEvent(BaseEvent[RawDanmakuFileCreatedEventData]):
    type: str = 'RawDanmakuFileCreatedEvent'
    data: RawDanmakuFileCreatedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RawDanmakuFileCompletedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class RawDanmakuFileCompletedEvent(BaseEvent[RawDanmakuFileCompletedEventData]):
    type: str = 'RawDanmakuFileCompletedEvent'
    data: RawDanmakuFileCompletedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class CoverImageDownloadedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class CoverImageDownloadedEvent(BaseEvent[CoverImageDownloadedEventData]):
    type: str = 'CoverImageDownloadedEvent'
    data: CoverImageDownloadedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class VideoPostprocessingCompletedEventData(BaseEventData):
    room_id: int
    path: str


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class VideoPostprocessingCompletedEvent(
    BaseEvent[VideoPostprocessingCompletedEventData]
):
    type: str = 'VideoPostprocessingCompletedEvent'
    data: VideoPostprocessingCompletedEventData


@attr.s(auto_attribs=True, slots=True, frozen=True)
class PostprocessingCompletedEventData(BaseEventData):
    room_id: int
    files: List[str]


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class PostprocessingCompletedEvent(BaseEvent[PostprocessingCompletedEventData]):
    type: str = 'PostprocessingCompletedEvent'
    data: PostprocessingCompletedEventData


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
class ErrorData(BaseEventData):
    name: str
    detail: str

    @classmethod
    def from_exc(cls, exc: BaseException) -> ErrorData:
        return cls(name=type(exc).__name__, detail=format_exception(exc))


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class Error(BaseEvent[ErrorData]):
    type: str = 'Error'
    data: ErrorData
