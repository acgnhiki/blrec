from __future__ import annotations

import logging
import os
from typing import Optional

import m3u8
from reactivex import Observable, abc
from reactivex import operators as ops
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from blrec.core import operators as core_ops
from blrec.utils import operators as utils_ops

from ..exceptions import NoNewSegments

__all__ = ('PlaylistResolver',)


logger = logging.getLogger(__name__)


class PlaylistResolver:
    def __init__(self, stream_url_resolver: core_ops.StreamURLResolver) -> None:
        self._stream_url_resolver = stream_url_resolver

    def __call__(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        return self._solve(source).pipe(
            ops.do_action(on_error=self._before_retry),
            utils_ops.retry(should_retry=self._should_retry),
        )

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

            attempts: int = 0
            last_sequence_number: Optional[int] = None

            def on_next(playlist: m3u8.M3U8) -> None:
                nonlocal attempts, last_sequence_number

                if playlist.is_endlist:
                    logger.debug('Playlist ended')

                new_segments = []
                for seg in playlist.segments:
                    num = self._sequence_number_of(seg.uri)
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
                    new_segments.append(seg)
                    last_sequence_number = num

                if not new_segments:
                    attempts += 1
                    if attempts > 3:
                        attempts = 0
                        observer.on_error(NoNewSegments())
                    return
                else:
                    attempts = 0

                for seg in new_segments:
                    observer.on_next(seg)

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

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, NoNewSegments):
            return True
        else:
            return False

    def _before_retry(self, exc: Exception) -> None:
        if not isinstance(exc, NoNewSegments):
            return
        logger.warning('No new segments received, trying to update the stream url.')
        self._stream_url_resolver.reset()
