from __future__ import annotations
from typing import List, TYPE_CHECKING

from .event_center import EventCenter
from .models import (
    LiveBeganEvent,
    LiveBeganEventData,
    LiveEndedEvent,
    LiveEndedEventData,
    RoomChangeEvent,
    RoomChangeEventData,
    RecordingStartedEvent,
    RecordingStartedEventData,
    RecordingFinishedEvent,
    RecordingFinishedEventData,
    RecordingCancelledEvent,
    RecordingCancelledEventData,
    VideoFileCreatedEvent,
    VideoFileCreatedEventData,
    VideoFileCompletedEvent,
    VideoFileCompletedEventData,
    DanmakuFileCreatedEvent,
    DanmakuFileCreatedEventData,
    DanmakuFileCompletedEvent,
    DanmakuFileCompletedEventData,
    RawDanmakuFileCreatedEvent,
    RawDanmakuFileCreatedEventData,
    RawDanmakuFileCompletedEvent,
    RawDanmakuFileCompletedEventData,
    CoverImageDownloadedEvent,
    CoverImageDownloadedEventData,
    VideoPostprocessingCompletedEvent,
    VideoPostprocessingCompletedEventData,
    PostprocessingCompletedEvent,
    PostprocessingCompletedEventData,
    SpaceNoEnoughEvent,
    SpaceNoEnoughEventData,
)
from ..bili.live import Live
from ..bili.models import RoomInfo
from ..bili.live_monitor import LiveEventListener
from ..core.recorder import RecorderEventListener
from ..disk_space import SpaceEventListener
from ..postprocess import PostprocessorEventListener

if TYPE_CHECKING:
    from ..bili.live_monitor import LiveMonitor
    from ..core.recorder import Recorder
    from ..disk_space import SpaceMonitor, DiskUsage
    from ..postprocess import Postprocessor


__all__ = ('LiveEventSubmitter', 'SpaceEventSubmitter', 'PostprocessorEventSubmitter')

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


class RecorderEventSubmitter(RecorderEventListener):
    def __init__(self, recorder: Recorder) -> None:
        super().__init__()
        recorder.add_listener(self)

    async def on_recording_started(self, recorder: Recorder) -> None:
        data = RecordingStartedEventData(recorder.live.room_info)
        event_center.submit(RecordingStartedEvent.from_data(data))

    async def on_recording_finished(self, recorder: Recorder) -> None:
        data = RecordingFinishedEventData(recorder.live.room_info)
        event_center.submit(RecordingFinishedEvent.from_data(data))

    async def on_recording_cancelled(self, recorder: Recorder) -> None:
        data = RecordingCancelledEventData(recorder.live.room_info)
        event_center.submit(RecordingCancelledEvent.from_data(data))

    async def on_video_file_created(self, recorder: Recorder, path: str) -> None:
        data = VideoFileCreatedEventData(recorder.live.room_id, path)
        event_center.submit(VideoFileCreatedEvent.from_data(data))

    async def on_video_file_completed(self, recorder: Recorder, path: str) -> None:
        data = VideoFileCompletedEventData(recorder.live.room_id, path)
        event_center.submit(VideoFileCompletedEvent.from_data(data))

    async def on_danmaku_file_created(self, recorder: Recorder, path: str) -> None:
        data = DanmakuFileCreatedEventData(recorder.live.room_id, path)
        event_center.submit(DanmakuFileCreatedEvent.from_data(data))

    async def on_danmaku_file_completed(self, recorder: Recorder, path: str) -> None:
        data = DanmakuFileCompletedEventData(recorder.live.room_id, path)
        event_center.submit(DanmakuFileCompletedEvent.from_data(data))

    async def on_raw_danmaku_file_created(self, recorder: Recorder, path: str) -> None:
        data = RawDanmakuFileCreatedEventData(recorder.live.room_id, path)
        event_center.submit(RawDanmakuFileCreatedEvent.from_data(data))

    async def on_raw_danmaku_file_completed(
        self, recorder: Recorder, path: str
    ) -> None:
        data = RawDanmakuFileCompletedEventData(recorder.live.room_id, path)
        event_center.submit(RawDanmakuFileCompletedEvent.from_data(data))

    async def on_cover_image_downloaded(self, recorder: Recorder, path: str) -> None:
        data = CoverImageDownloadedEventData(recorder.live.room_id, path)
        event_center.submit(CoverImageDownloadedEvent.from_data(data))


class PostprocessorEventSubmitter(PostprocessorEventListener):
    def __init__(self, postprocessor: Postprocessor) -> None:
        super().__init__()
        postprocessor.add_listener(self)

    async def on_video_postprocessing_completed(
        self, postprocessor: Postprocessor, path: str
    ) -> None:
        data = VideoPostprocessingCompletedEventData(
            postprocessor.recorder.live.room_id, path
        )
        event_center.submit(VideoPostprocessingCompletedEvent.from_data(data))

    async def on_postprocessing_completed(
        self, postprocessor: Postprocessor, files: List[str]
    ) -> None:
        data = PostprocessingCompletedEventData(
            postprocessor.recorder.live.room_id, files
        )
        event_center.submit(PostprocessingCompletedEvent.from_data(data))


class SpaceEventSubmitter(SpaceEventListener):
    def __init__(self, space_monitor: SpaceMonitor) -> None:
        super().__init__()
        space_monitor.add_listener(self)

    async def on_space_no_enough(
        self, path: str, threshold: int, disk_usage: DiskUsage
    ) -> None:
        data = SpaceNoEnoughEventData(path, threshold, disk_usage)
        event_center.submit(SpaceNoEnoughEvent.from_data(data))
