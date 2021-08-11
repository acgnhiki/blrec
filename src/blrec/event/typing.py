from typing import Union


from .models import (
    LiveBeganEvent,
    LiveBeganEventData,
    LiveEndedEvent,
    LiveEndedEventData,
    RoomChangeEvent,
    RoomChangeEventData,
    SpaceNoEnoughEvent,
    SpaceNoEnoughEventData,
    FileCompletedEvent,
    FileCompletedEventData,
    Error,
    ErrorData,
)


Event = Union[
    LiveBeganEvent,
    LiveEndedEvent,
    RoomChangeEvent,
    SpaceNoEnoughEvent,
    FileCompletedEvent,
    Error,
]

EventData = Union[
    LiveBeganEventData,
    LiveEndedEventData,
    RoomChangeEventData,
    SpaceNoEnoughEventData,
    FileCompletedEventData,
    ErrorData,
]
