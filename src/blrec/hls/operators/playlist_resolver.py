from __future__ import annotations

import logging
import os
from typing import Optional

import m3u8
import urllib3
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

__all__ = ('PlaylistResolver',)


logger = logging.getLogger(__name__)
logging.getLogger(urllib3.__name__).setLevel(logging.WARNING)


class PlaylistResolver:
    def __call__(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        return self._solve(source)

    def _name_of(self, uri: str) -> str:
        name, ext = os.path.splitext(uri)
        return name

    def _sequence_number_of(self, uri: str) -> int:
        return int(self._name_of(uri))

    def _solve(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        def subscribe(
            observer: abc.ObserverBase[m3u8.Segment],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            last_sequence_number: Optional[int] = None

            def on_next(playlist: m3u8.M3U8) -> None:
                nonlocal last_sequence_number

                if playlist.is_endlist:
                    logger.debug('Playlist ended')

                for seg in playlist.segments:
                    uri = seg.uri
                    name = self._name_of(uri)
                    num = int(name)
                    if last_sequence_number is not None:
                        if last_sequence_number >= num:
                            continue
                        if last_sequence_number + 1 != num:
                            logger.warning(
                                'Segments discontinuous: '
                                f'last sequence number: {last_sequence_number}, '
                                f'current sequence number: {num}'
                            )
                            seg.discontinuity = True
                    observer.on_next(seg)
                    last_sequence_number = num

            def dispose() -> None:
                nonlocal disposed
                nonlocal last_sequence_number
                disposed = True
                last_sequence_number = None

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
