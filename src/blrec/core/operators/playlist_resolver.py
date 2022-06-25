from __future__ import annotations

import logging
from typing import Final, Optional, Set

import m3u8
import urllib3
from ordered_set import OrderedSet
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

__all__ = ('PlaylistResolver',)


logger = logging.getLogger(__name__)
logging.getLogger(urllib3.__name__).setLevel(logging.WARNING)


class PlaylistResolver:
    _MAX_LAST_SEG_URIS: Final[int] = 30

    def __call__(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        return self._solve(source)

    def _solve(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        def subscribe(
            observer: abc.ObserverBase[m3u8.Segment],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            last_seg_uris: OrderedSet[str] = OrderedSet()

            def on_next(playlist: m3u8.M3U8) -> None:
                curr_seg_uris: Set[str] = set()

                for seg in playlist.segments:
                    if disposed:
                        return
                    curr_seg_uris.add(seg.uri)
                    if seg.uri not in last_seg_uris:
                        observer.on_next(seg)
                        last_seg_uris.add(seg.uri)
                        if len(last_seg_uris) > self._MAX_LAST_SEG_URIS:
                            last_seg_uris.pop(0)

                if last_seg_uris and not curr_seg_uris.intersection(last_seg_uris):
                    logger.debug(
                        'Segments broken!\n'
                        f'Last segments uris: {last_seg_uris}\n'
                        f'Current segments uris: {curr_seg_uris}'
                    )

                if playlist.is_endlist:
                    logger.debug('Playlist ended')

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                last_seg_uris.clear()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
