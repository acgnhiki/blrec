import logging
import math
from typing import Callable, Optional

from reactivex import Observable, abc

from ..common import (
    is_audio_tag,
    is_metadata_tag,
    is_script_tag,
    is_video_tag,
    parse_metadata,
)
from ..models import AudioTag, FlvHeader, FlvTag, ScriptTag, VideoTag
from .typing import FLVStream, FLVStreamItem

__all__ = ('fix',)

logger = logging.getLogger(__name__)


def fix() -> Callable[[FLVStream], FLVStream]:
    def _fix(source: FLVStream) -> FLVStream:
        """Fix broken timestamps of the FLV tags."""

        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            delta: int = 0
            last_tag: Optional[FlvTag] = None
            last_audio_tag: Optional[AudioTag] = None
            last_video_tag: Optional[VideoTag] = None
            frame_rate = 30.0
            video_frame_interval = math.ceil(1000 / frame_rate)
            sound_sample_interval = math.ceil(1000 / 44)

            def reset() -> None:
                nonlocal delta, last_tag, last_audio_tag, last_video_tag
                nonlocal frame_rate, video_frame_interval, sound_sample_interval
                delta = 0
                last_tag = None
                last_audio_tag = None
                last_video_tag = None
                frame_rate = 30.0
                video_frame_interval = math.ceil(1000 / frame_rate)
                sound_sample_interval = math.ceil(1000 / 44)

            def update_parameters(tag: ScriptTag) -> None:
                nonlocal frame_rate, video_frame_interval
                metadata = parse_metadata(tag)
                fps = metadata.get('fps') or metadata.get('framerate')

                if not fps:
                    return

                frame_rate = fps
                video_frame_interval = math.ceil(1000 / frame_rate)

                logger.debug(
                    'frame rate: {}, video frame interval: {}'.format(
                        frame_rate, video_frame_interval
                    )
                )

            def update_last_tags(tag: FlvTag) -> None:
                nonlocal last_tag, last_audio_tag, last_video_tag
                last_tag = tag
                if is_audio_tag(tag):
                    last_audio_tag = tag
                elif is_video_tag(tag):
                    last_video_tag = tag

            def update_delta(tag: FlvTag) -> None:
                nonlocal delta
                assert last_tag is not None
                delta = last_tag.timestamp + delta - tag.timestamp + calc_interval(tag)

            def correct_ts(tag: FlvTag) -> FlvTag:
                if delta == 0:
                    return tag
                return tag.evolve(timestamp=tag.timestamp + delta)

            def calc_interval(tag: FlvTag) -> int:
                if is_audio_tag(tag):
                    return sound_sample_interval
                elif is_video_tag(tag):
                    return video_frame_interval
                else:
                    logger.warning(f'Unexpected tag type: {tag}')
                    return min(sound_sample_interval, video_frame_interval)

            def is_ts_rebounded(tag: FlvTag) -> bool:
                if is_audio_tag(tag):
                    if last_audio_tag is None:
                        return False
                    return tag.timestamp < last_audio_tag.timestamp
                elif is_video_tag(tag):
                    if last_video_tag is None:
                        return False
                    return tag.timestamp < last_video_tag.timestamp
                else:
                    return False

            def is_ts_incontinuous(tag: FlvTag) -> bool:
                if last_tag is None:
                    return False
                return tag.timestamp - last_tag.timestamp > max(
                    sound_sample_interval, video_frame_interval
                )

            def on_next(item: FLVStreamItem) -> None:
                if isinstance(item, FlvHeader):
                    reset()
                    observer.on_next(item)
                    return

                tag = item

                if is_script_tag(tag):
                    if is_metadata_tag(tag):
                        update_parameters(tag)
                    observer.on_next(tag)
                    return

                if is_ts_rebounded(tag):
                    update_delta(tag)
                    logger.warning(
                        f'Timestamp rebounded, updated delta: {delta}\n'
                        f'last audio tag: {last_audio_tag}\n'
                        f'last video tag: {last_video_tag}\n'
                        f'current tag: {tag}'
                    )
                elif is_ts_incontinuous(tag):
                    update_delta(tag)
                    logger.warning(
                        f'Timestamp incontinuous, updated delta: {delta}\n'
                        f'last tag: {last_tag}\n'
                        f'current tag: {tag}'
                    )

                update_last_tags(tag)
                tag = correct_ts(tag)
                observer.on_next(tag)

            return source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    return _fix
