from __future__ import annotations

from typing import Optional

import m3u8
from loguru import logger
from reactivex import Observable, abc
from reactivex import operators as ops
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from blrec.core import operators as core_ops
from blrec.utils import operators as utils_ops

from ..exceptions import NoNewSegments
from ..helpler import sequence_number_of

__all__ = ('PlaylistResolver',)


class PlaylistResolver:
    def __init__(self, stream_url_resolver: core_ops.StreamURLResolver) -> None:
        self._stream_url_resolver = stream_url_resolver
        self._last_media_sequence: int = 0
        self._last_sequence_number: Optional[int] = None

    def __call__(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        return self._solve(source).pipe(
            ops.do_action(on_error=self._before_retry),
            utils_ops.retry(should_retry=self._should_retry),
        )

    def _solve(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        self._last_media_sequence = 0
        self._last_sequence_number = None

        def subscribe(
            observer: abc.ObserverBase[m3u8.Segment],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            attempts: int = 0

            def on_next(playlist: m3u8.M3U8) -> None:
                nonlocal attempts
                discontinuity = False

                if playlist.is_endlist:
                    logger.debug('Playlist ended')

                if playlist.media_sequence < self._last_media_sequence:
                    logger.warning(
                        'Segments discontinuous: '
                        f'last media sequence: {self._last_media_sequence}, '
                        f'current media sequence: {playlist.media_sequence}'
                    )
                    discontinuity = True
                    self._last_sequence_number = None
                self._last_media_sequence = playlist.media_sequence

                new_segments = []
                for seg in playlist.segments:
                    num = sequence_number_of(seg.uri)
                    if self._last_sequence_number is not None:
                        if num <= self._last_sequence_number:
                            continue
                        if num == self._last_sequence_number + 1:
                            discontinuity = False
                        else:
                            logger.warning(
                                'Segments discontinuous: '
                                f'last sequence number: {self._last_sequence_number}, '
                                f'current sequence number: {num}'
                            )
                            discontinuity = True
                    seg.discontinuity = discontinuity
                    seg.custom_parser_values['playlist'] = playlist
                    new_segments.append(seg)
                    self._last_sequence_number = num

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
                disposed = True

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
