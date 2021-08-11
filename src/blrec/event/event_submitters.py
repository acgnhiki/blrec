from __future__ import annotations
from typing import TYPE_CHECKING

from .event_center import EventCenter
from .models import (
    LiveBeganEvent,
    LiveBeganEventData,
    LiveEndedEvent,
    LiveEndedEventData,
    RoomChangeEvent,
    RoomChangeEventData,
    FileCompletedEvent,
    FileCompletedEventData,
    SpaceNoEnoughEvent,
    SpaceNoEnoughEventData,
)
from ..bili.live import Live
from ..bili.models import RoomInfo
from ..bili.live_monitor import LiveEventListener
from ..disk_space import SpaceEventListener
from ..postprocess import PostprocessorEventListener
if TYPE_CHECKING:
    from ..bili.live_monitor import LiveMonitor
    from ..disk_space import SpaceMonitor, DiskUsage
    from ..postprocess import Postprocessor


__all__ = (
    'LiveEventSubmitter',
    'SpaceEventSubmitter',
    'PostprocessorEventSubmitter',
)

event_center = EventCenter.get_instance()


class LiveEventSubmitter(LiveEventListener):
    def __init__(self, live_monitor: LiveMonitor) -> None:
        super().__init__()
        live_monitor.add_listener(self)

    async def on_live_began(self, live: Live) -> None:
        data = LiveBeganEventData(live.user_info, live.room_info)
        event_center.submit(LiveBeganEvent.from_data(data))

    async def on_live_ended(self, live: Live) -> None:
        data = LiveEndedEventData(live.user_info, live.room_info)
        event_center.submit(LiveEndedEvent.from_data(data))

    async def on_room_changed(self, room_info: RoomInfo) -> None:
        data = RoomChangeEventData(room_info)
        event_center.submit(RoomChangeEvent.from_data(data))


class SpaceEventSubmitter(SpaceEventListener):
    def __init__(self, space_monitor: SpaceMonitor) -> None:
        super().__init__()
        space_monitor.add_listener(self)

    async def on_space_no_enough(
        self, path: str, threshold: int, disk_usage: DiskUsage
    ) -> None:
        data = SpaceNoEnoughEventData(path, threshold, disk_usage)
        event_center.submit(SpaceNoEnoughEvent.from_data(data))


class PostprocessorEventSubmitter(PostprocessorEventListener):
    def __init__(self, postprocessor: Postprocessor) -> None:
        super().__init__()
        postprocessor.add_listener(self)

    async def on_file_completed(self, room_id: int, path: str) -> None:
        data = FileCompletedEventData(room_id, path)
        event_center.submit(FileCompletedEvent.from_data(data))
