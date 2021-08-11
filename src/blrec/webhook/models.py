from __future__ import annotations
import logging
from typing import Set, Tuple, Type

import attr

from ..setting import WebHookSettings
from ..event import (
    LiveBeganEvent,
    LiveEndedEvent,
    RoomChangeEvent,
    SpaceNoEnoughEvent,
    FileCompletedEvent,
)
from ..event.typing import Event


__all__ = 'WebHook',


logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class WebHook:
    url: str
    event_types: Tuple[Type[Event], ...]
    receive_exception: bool

    @classmethod
    def from_settings(cls, settings: WebHookSettings) -> WebHook:
        types: Set[Type[Event]] = set()

        if settings.live_began:
            types.add(LiveBeganEvent)
        if settings.live_ended:
            types.add(LiveEndedEvent)
        if settings.room_change:
            types.add(RoomChangeEvent)
        if settings.file_completed:
            types.add(FileCompletedEvent)
        if settings.space_no_enough:
            types.add(SpaceNoEnoughEvent)

        return cls(
            url=settings.url,
            event_types=tuple(types),
            receive_exception=settings.error_occurred,
        )
