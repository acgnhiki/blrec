from __future__ import annotations

from typing import Optional, Union

import attr
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from .playlist_dumper import PlaylistDumper
from .prober import Prober, StreamProfile
from .segment_dumper import SegmentDumper
from .segment_fetcher import InitSectionData, SegmentData

__all__ = ('Analyser', 'MetaData')


@attr.s(auto_attribs=True, slots=True, frozen=True, kw_only=True)
class MetaData:
    duration: float
    filesize: int
    width: int
    height: int


class Analyser:
    def __init__(
        self,
        playlist_dumper: PlaylistDumper,
        segment_dumper: SegmentDumper,
        prober: Prober,
    ) -> None:
        self._playlist_dumper = playlist_dumper
        self._segment_dumper = segment_dumper
        self._prober = prober

        self._reset()
        self._prober.profiles.subscribe(self._on_profile_updated)

    def _reset(self) -> None:
        self._video_width: int = 0
        self._video_height: int = 0

    def _on_profile_updated(self, profile: StreamProfile) -> None:
        video_profile = profile['streams'][0]
        assert video_profile['codec_type'] == 'video'
        self._video_width = video_profile['width']
        self._video_height = video_profile['height']

    def make_metadata(self) -> MetaData:
        return MetaData(
            duration=self._playlist_dumper.duration,
            filesize=self._segment_dumper.filesize,
            width=self._video_width,
            height=self._video_height,
        )

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._analyse(source)

    def _analyse(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        def subscribe(
            observer: abc.ObserverBase[Union[InitSectionData, SegmentData]],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            self._reset()

            def on_next(item: Union[InitSectionData, SegmentData]) -> None:
                observer.on_next(item)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                self._reset()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
