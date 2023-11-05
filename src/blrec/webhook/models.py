from __future__ import annotations

from typing import Set, Tuple, Type

import attr

from ..event import (
    CoverImageDownloadedEvent,
    DanmakuFileCompletedEvent,
    DanmakuFileCreatedEvent,
    LiveBeganEvent,
    LiveEndedEvent,
    PostprocessingCompletedEvent,
    RawDanmakuFileCompletedEvent,
    RawDanmakuFileCreatedEvent,
    RecordingCancelledEvent,
    RecordingFinishedEvent,
    RecordingStartedEvent,
    RoomChangeEvent,
    SpaceNoEnoughEvent,
    VideoFileCompletedEvent,
    VideoFileCreatedEvent,
    VideoPostprocessingCompletedEvent,
)
from ..event.typing import Event
from ..setting import WebHookSettings

__all__ = ('WebHook',)


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
        if settings.recording_started:
            types.add(RecordingStartedEvent)
        if settings.recording_finished:
            types.add(RecordingFinishedEvent)
        if settings.recording_cancelled:
            types.add(RecordingCancelledEvent)
        if settings.video_file_created:
            types.add(VideoFileCreatedEvent)
        if settings.video_file_completed:
            types.add(VideoFileCompletedEvent)
        if settings.danmaku_file_created:
            types.add(DanmakuFileCreatedEvent)
        if settings.danmaku_file_completed:
            types.add(DanmakuFileCompletedEvent)
        if settings.raw_danmaku_file_created:
            types.add(RawDanmakuFileCreatedEvent)
        if settings.raw_danmaku_file_completed:
            types.add(RawDanmakuFileCompletedEvent)
        if settings.cover_image_downloaded:
            types.add(CoverImageDownloadedEvent)
        if settings.video_postprocessing_completed:
            types.add(VideoPostprocessingCompletedEvent)
        if settings.postprocessing_completed:
            types.add(PostprocessingCompletedEvent)
        if settings.space_no_enough:
            types.add(SpaceNoEnoughEvent)

        return cls(
            url=settings.url,
            event_types=tuple(types),
            receive_exception=settings.error_occurred,
        )
