from __future__ import annotations

from enum import IntEnum, auto
from typing import Callable, List, Optional, TypedDict, cast

import attr
from loguru import logger
from reactivex import Observable, Subject, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from typing_extensions import TypeGuard

from ...utils.hash import cksum
from ..common import (
    create_script_tag,
    is_audio_sequence_header,
    is_metadata_tag,
    is_script_tag,
    is_sequence_header,
    is_video_sequence_header,
    parse_scriptdata,
)
from ..models import AudioTag, FlvHeader, FlvTag, ScriptTag, VideoTag
from ..scriptdata import ScriptData
from ..utils import format_timestamp
from .typing import FLVStream, FLVStreamItem

__all__ = ('concat', 'JoinPointExtractor', 'JoinPoint', 'JoinPointData')


@attr.s(auto_attribs=True, slots=True, frozen=True)
class JoinPoint:
    seamless: bool
    timestamp: float  # timestamp of next tag in milliseconds
    crc32: str  # crc32 of the next tag

    @classmethod
    def from_metadata_value(cls, value: JoinPointData) -> JoinPoint:
        return cls(
            timestamp=int(value['timestamp']),
            seamless=value['seamless'],
            crc32=value['crc32'],
        )

    def to_metadata_value(self) -> JoinPointData:
        return dict(
            timestamp=float(self.timestamp), seamless=self.seamless, crc32=self.crc32
        )

    def __str__(self) -> str:
        return 'seamless: {}, timestamp: {}, crc32: {}'.format(
            'yes' if self.seamless else 'no',
            format_timestamp(int(self.timestamp)),
            self.crc32,
        )


class JoinPointData(TypedDict):
    seamless: bool
    timestamp: float
    crc32: str


class ACTION(IntEnum):
    NOOP = auto()
    CORRECT = auto()
    GATHER = auto()
    CANCEL = auto()
    CONCAT = auto()
    CONCAT_AND_GATHER = auto()


def concat(
    num_of_last_tags: int = 3, max_duration: int = 20_000
) -> Callable[[FLVStream], FLVStream]:
    """Concat FLV streams.

    num_of_last_tags: Number of tags for determining whether or not tags are duplicated
    max_duration: Max duration in milliseconds the duplicated tags might last
    """

    def _concat(source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            delta: int = 0
            action: ACTION = ACTION.NOOP
            last_tags: List[FlvTag] = []
            gathered_tags: List[FlvTag] = []
            last_flv_header: Optional[FlvHeader] = None
            last_audio_sequence_header: Optional[AudioTag] = None
            last_video_sequence_header: Optional[VideoTag] = None

            def reset() -> None:
                nonlocal delta
                nonlocal action
                nonlocal last_tags
                nonlocal gathered_tags
                nonlocal last_flv_header
                nonlocal last_audio_sequence_header
                nonlocal last_video_sequence_header
                delta = 0
                action = ACTION.NOOP
                last_tags = []
                gathered_tags = []
                last_flv_header = None
                last_audio_sequence_header = None
                last_video_sequence_header = None

            def update_last_tags(tag: FlvTag) -> None:
                nonlocal last_audio_sequence_header, last_video_sequence_header
                last_tags.append(tag)
                if len(last_tags) > num_of_last_tags:
                    last_tags.pop(0)
                if is_audio_sequence_header(tag):
                    last_audio_sequence_header = tag
                elif is_video_sequence_header(tag):
                    last_video_sequence_header = tag

            def gather_tags(tag: FlvTag) -> None:
                nonlocal gathered_tags
                nonlocal action
                nonlocal last_audio_sequence_header, last_video_sequence_header
                if is_audio_sequence_header(tag):
                    if last_audio_sequence_header is None:
                        logger.debug(
                            'Cancel concat due to no last audio sequence header'
                        )
                        action = ACTION.CANCEL
                    else:
                        if not tag.is_the_same_as(last_audio_sequence_header):
                            action = ACTION.CANCEL
                            logger.debug(
                                'Cancel concat due to audio sequence header changed'
                            )
                    last_audio_sequence_header = tag
                elif is_video_sequence_header(tag):
                    if last_video_sequence_header is None:
                        logger.debug(
                            'Cancel concat due to no last video sequence header'
                        )
                        action = ACTION.CANCEL
                    else:
                        if not tag.is_the_same_as(last_video_sequence_header):
                            action = ACTION.CANCEL
                            logger.debug(
                                'Cancel concat due to video sequence header changed'
                            )
                    last_video_sequence_header = tag
                gathered_tags.append(tag)

            def has_gathering_completed() -> bool:
                # XXX: timestamp MUST start from 0 and continuous!
                # put the correct and fix operator on upstream of this operator
                # to ensure timestamp start from 0 and continuous!
                return gathered_tags[-1].timestamp >= max_duration

            def find_last_duplicated_tag(tags: List[FlvTag]) -> int:
                logger.debug('Finding duplicated tags...')

                last_out_tag = last_tags[-1]
                logger.debug(f'The last output tag is {last_out_tag}')

                for idx, tag in enumerate(tags):
                    if not tag.is_the_same_as(last_out_tag):
                        continue

                    if not all(
                        map(
                            lambda t: t[0].is_the_same_as(t[1]),
                            zip(
                                tags[max(0, idx - (len(last_tags) - 1)) : idx],
                                last_tags[:-1],
                            ),
                        )
                    ):
                        continue

                    logger.debug(f'The last duplicated tag found at {idx} is {tag}')
                    return idx

                logger.debug('No duplicated tag found')
                return -1

            def update_delta_duplicated(last_duplicated_tag: FlvTag) -> None:
                nonlocal delta
                delta = last_tags[-1].timestamp - last_duplicated_tag.timestamp

            def update_delta_no_duplicated(first_data_tag: FlvTag) -> None:
                nonlocal delta
                delta = last_tags[-1].timestamp - first_data_tag.timestamp + 10

            def correct_ts(tag: FlvTag) -> FlvTag:
                if delta == 0:
                    return tag
                return tag.evolve(timestamp=tag.timestamp + delta)

            def make_join_point_tag(next_tag: FlvTag, seamless: bool) -> ScriptTag:
                assert next_tag.body
                join_point = JoinPoint(
                    seamless=seamless,
                    timestamp=float(next_tag.timestamp),
                    crc32=cksum(next_tag.body),
                )
                logger.debug(f'join point: {join_point}; next tag: {next_tag}')
                script_data = ScriptData(
                    name='onJoinPoint', value=attr.asdict(join_point)
                )
                script_tag = create_script_tag(script_data)
                return script_tag

            def do_concat() -> None:
                logger.debug(
                    'Concatenating... gathered {} tags, total size: {}'.format(
                        len(gathered_tags), sum(t.tag_size for t in gathered_tags)
                    )
                )

                tags = list(
                    filter(
                        lambda tag: not is_metadata_tag(tag)
                        and not is_sequence_header(tag),
                        gathered_tags,
                    )
                )
                logger.debug(
                    '{} data tags, total size: {}'.format(
                        len(tags), sum(t.tag_size for t in tags)
                    )
                )

                if not tags:
                    return

                if (index := find_last_duplicated_tag(tags)) >= 0:
                    seamless = True
                    update_delta_duplicated(tags[index])
                    logger.debug(f'Updated delta: {delta}, seamless: {seamless}')
                    tags = tags[index + 1 :]
                else:
                    seamless = False
                    update_delta_no_duplicated(tags[0])
                    logger.debug(f'Updated delta: {delta}, seamless: {seamless}')

                if tags:
                    join_point_tag = make_join_point_tag(correct_ts(tags[0]), seamless)
                    observer.on_next(join_point_tag)

                for tag in tags:
                    tag = correct_ts(tag)
                    update_last_tags(tag)
                    observer.on_next(tag)

                gathered_tags.clear()

            def do_cancel() -> None:
                logger.debug(
                    'Cancelling... gathered {} tags, total size: {}'.format(
                        len(gathered_tags), sum(t.tag_size for t in gathered_tags)
                    )
                )
                assert last_flv_header is not None
                observer.on_next(last_flv_header)
                for tag in gathered_tags:
                    update_last_tags(tag)
                    observer.on_next(tag)
                gathered_tags.clear()

            def on_next(item: FLVStreamItem) -> None:
                nonlocal action
                nonlocal last_flv_header

                if isinstance(item, FlvHeader):
                    if last_flv_header is None:
                        logger.debug('No operation needed for the first stream')
                        last_flv_header = item
                        action = ACTION.NOOP
                        observer.on_next(item)
                    else:
                        logger.debug('Gathering tags for deduplication...')
                        last_flv_header = item
                        if action == ACTION.GATHER:
                            action = ACTION.CONCAT_AND_GATHER
                        else:
                            action = ACTION.GATHER
                    return

                tag = item

                while True:
                    if action == ACTION.NOOP:
                        update_last_tags(tag)
                        observer.on_next(tag)
                        return

                    if action == ACTION.CORRECT:
                        tag = correct_ts(tag)
                        update_last_tags(tag)
                        observer.on_next(tag)
                        return

                    if action in (ACTION.CONCAT, ACTION.CONCAT_AND_GATHER):
                        do_concat()
                        if action == ACTION.CONCAT_AND_GATHER:
                            action = ACTION.GATHER
                        else:
                            action = ACTION.CORRECT
                            return

                    if action == ACTION.GATHER:
                        gather_tags(tag)
                        if action == ACTION.CANCEL:
                            do_cancel()
                            action = ACTION.NOOP
                            return
                        if has_gathering_completed():
                            action = ACTION.CONCAT
                            continue

                    break

            def on_completed() -> None:
                if action == ACTION.GATHER:
                    do_concat()
                observer.on_completed()

            def on_error(e: Exception) -> None:
                if action == ACTION.GATHER:
                    do_concat()
                observer.on_error(e)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                reset()

            subscription.disposable = source.subscribe(
                on_next, on_error, on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    return _concat


class JoinPointExtractor:
    def __init__(self) -> None:
        self._join_points: Subject[List[JoinPoint]] = Subject()

    @property
    def join_points(self) -> Observable[List[JoinPoint]]:
        return self._join_points

    def __call__(self, source: FLVStream) -> FLVStream:
        return self._extract(source)

    def _extract(self, source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            stream_index: int = -1
            join_points: List[JoinPoint] = []
            join_point_tag: Optional[ScriptTag] = None

            def reset() -> None:
                nonlocal stream_index, join_points, join_point_tag
                stream_index = -1
                join_points = []
                join_point_tag = None

            def push_join_points() -> None:
                self._join_points.on_next(join_points.copy())

            def on_next(item: FLVStreamItem) -> None:
                nonlocal stream_index
                nonlocal join_point_tag

                if isinstance(item, FlvHeader):
                    stream_index += 1
                    if stream_index > 0:
                        push_join_points()
                        join_points.clear()
                    join_point_tag = None
                    observer.on_next(item)
                    return

                if join_point_tag:
                    join_point = self._make_join_point(join_point_tag, item)
                    join_points.append(join_point)
                    join_point_tag = None

                if self._is_join_point_tag(item):
                    join_point_tag = item
                    return

                observer.on_next(item)

            def on_completed() -> None:
                push_join_points()
                observer.on_completed()

            def on_error(e: Exception) -> None:
                push_join_points()
                observer.on_error(e)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                push_join_points()
                reset()

            subscription.disposable = source.subscribe(
                on_next, on_error, on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    def _is_join_point_tag(self, tag: FlvTag) -> TypeGuard[ScriptTag]:
        if is_script_tag(tag):
            script_data = parse_scriptdata(tag)
            return script_data['name'] == 'onJoinPoint'
        return False

    def _make_join_point(
        self, join_point_tag: ScriptTag, next_tag: FlvTag
    ) -> JoinPoint:
        script_data = parse_scriptdata(join_point_tag)
        join_point_data = cast(JoinPointData, script_data['value'])
        assert next_tag.body, next_tag
        join_point = JoinPoint(
            seamless=join_point_data['seamless'],
            timestamp=next_tag.timestamp,
            crc32=join_point_data['crc32'],
        )
        logger.debug(f'Extracted join point: {join_point}; next tag: {next_tag}')
        if cksum(next_tag.body) != join_point_data['crc32']:
            logger.warning(
                f'Timestamp of extracted join point may be incorrect\n'
                f'join point data: {join_point_data}\n'
                f'join point tag: {join_point_tag}\n'
                f'next tag: {next_tag}\n'
            )
        return join_point
