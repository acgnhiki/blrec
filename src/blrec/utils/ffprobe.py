from __future__ import annotations

import json
from subprocess import PIPE, Popen
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from reactivex import Observable, abc
from reactivex.scheduler import CurrentThreadScheduler

__all__ = (
    'ffprobe',
    'ffprobe_on',
    'StreamProfile',
    'FormatProfile',
    'VideoProfile',
    'AudioProfile',
)


class VideoProfile(TypedDict, total=False):
    index: int
    codec_name: str
    codec_long_name: str
    codec_type: Literal['video']
    codec_tag_string: str
    codec_tag: str
    width: int
    height: int
    coded_width: int
    coded_height: int
    closed_captions: int
    film_grain: int
    has_b_frames: int
    level: int
    refs: int
    is_avc: str
    nal_length_size: str
    id: str
    r_frame_rate: str
    avg_frame_rate: str
    time_base: str
    duration_ts: int
    duration: str
    extradata_size: int
    disposition: Dict[str, int]
    tags: Dict[str, Any]


class AudioProfile(TypedDict, total=False):
    index: int
    codec_name: str
    codec_long_name: str
    codec_type: Literal['audio']
    codec_tag_string: str
    codec_tag: str
    sample_fmt: str
    sample_rate: str
    channels: int
    channel_layout: str
    bits_per_sample: int
    id: str
    r_frame_rate: str
    avg_frame_rate: str
    time_base: str
    duration_ts: int
    duration: str
    bit_rate: str
    extradata_size: int
    disposition: Dict[str, int]
    tags: Dict[str, Any]


class FormatProfile(TypedDict, total=False):
    filename: str
    nb_streams: int
    nb_programs: int
    format_name: str
    format_long_name: str
    size: str
    probe_score: int
    tags: Dict[str, Any]


class StreamProfile(TypedDict, total=False):
    streams: List[Union[VideoProfile, AudioProfile]]
    format: FormatProfile


def ffprobe(data: bytes) -> StreamProfile:
    args = [
        'ffprobe',
        '-show_streams',
        '-show_format',
        '-print_format',
        'json',
        'pipe:0',
    ]

    with Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE) as process:
        try:
            stdout, _stderr = process.communicate(data, timeout=10)
            profile = json.loads(stdout)
        except Exception:
            process.kill()
            process.wait()
            raise
        else:
            return profile


def ffprobe_on(data: bytes) -> Observable[StreamProfile]:
    def subscribe(
        observer: abc.ObserverBase[StreamProfile],
        scheduler: Optional[abc.SchedulerBase] = None,
    ) -> abc.DisposableBase:
        _scheduler = scheduler or CurrentThreadScheduler()

        def action(scheduler: abc.SchedulerBase, state: Optional[Any] = None) -> None:
            try:
                profile = ffprobe(data)
            except Exception as e:
                observer.on_error(e)
            else:
                observer.on_next(profile)
                observer.on_completed()

        return _scheduler.schedule(action)

    return Observable(subscribe)
