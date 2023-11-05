from typing import Callable, List, Optional

from loguru import logger
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from ..common import (
    find_aac_header_tag,
    find_avc_header_tag,
    find_metadata_tag,
    is_audio_tag,
    is_avc_end_sequence,
    is_script_tag,
    is_video_nalu_keyframe,
    is_video_tag,
)
from ..models import AudioTag, FlvHeader, FlvTag, ScriptTag, VideoTag
from .typing import FLVStream, FLVStreamItem

__all__ = ('sort',)


def sort() -> Callable[[FLVStream], FLVStream]:
    "Sort tags in GOP by timestamp to ensure subsequent operators work as expected."

    def _sort(source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            gop_tags: List[FlvTag] = []

            def reset() -> None:
                nonlocal gop_tags
                gop_tags = []

            def push_gop_tags() -> None:
                if not gop_tags:
                    return

                logger.opt(lazy=True).trace(
                    'Tags in GOP:\n'
                    'Number of tags: {}\n'
                    'Total size of tags: {}\n'
                    'The first tag is {}\n'
                    'The last tag is {}',
                    lambda: len(gop_tags),
                    lambda: sum(map(len, gop_tags)),
                    lambda: gop_tags[0],
                    lambda: gop_tags[-1],
                )

                if len(gop_tags) < 10:
                    avc_header_tag = find_avc_header_tag(gop_tags)
                    aac_header_tag = find_aac_header_tag(gop_tags)
                    if avc_header_tag is not None and aac_header_tag is not None:
                        if (metadata_tag := find_metadata_tag(gop_tags)) is not None:
                            observer.on_next(metadata_tag)
                        observer.on_next(avc_header_tag)
                        observer.on_next(aac_header_tag)
                        gop_tags.clear()
                        return

                script_tags: List[ScriptTag] = []
                video_tags: List[VideoTag] = []
                audio_tags: List[AudioTag] = []
                for tag in gop_tags:
                    if is_video_tag(tag):
                        video_tags.append(tag)
                    elif is_audio_tag(tag):
                        audio_tags.append(tag)
                    elif is_script_tag(tag):
                        script_tags.append(tag)

                sorted_tags: List[FlvTag] = []
                i = len(audio_tags) - 1
                for video_tag in reversed(video_tags):
                    sorted_tags.insert(0, video_tag)
                    while i >= 0 and audio_tags[i].timestamp >= video_tag.timestamp:
                        sorted_tags.insert(1, audio_tags[i])
                        i -= 1

                for tag in script_tags:
                    observer.on_next(tag)

                for tag in sorted_tags:
                    observer.on_next(tag)

                gop_tags.clear()

            def on_next(item: FLVStreamItem) -> None:
                if isinstance(item, FlvHeader) or is_avc_end_sequence(item):
                    push_gop_tags()
                    observer.on_next(item)
                    return

                if is_video_nalu_keyframe(item):
                    push_gop_tags()
                    gop_tags.append(item)
                else:
                    gop_tags.append(item)

            def on_completed() -> None:
                push_gop_tags()
                observer.on_completed()

            def on_error(exc: Exception) -> None:
                push_gop_tags()
                observer.on_error(exc)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                if gop_tags:
                    logger.debug(
                        'Remaining tags:\n'
                        f'Number of tags: {len(gop_tags)}\n'
                        f'Total size of tags: {sum(map(len, gop_tags))}\n'
                        f'The first tag is {gop_tags[0]}\n'
                        f'The last tag is {gop_tags[-1]}'
                    )
                reset()

            subscription.disposable = source.subscribe(
                on_next, on_error, on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    return _sort
