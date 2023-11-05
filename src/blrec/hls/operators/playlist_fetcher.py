from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import m3u8
import requests
import urllib3
from loguru import logger
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_exponential

from blrec.bili.live import Live
from blrec.utils.mixins import SupportDebugMixin

__all__ = ('PlaylistFetcher',)


class PlaylistFetcher(SupportDebugMixin):
    def __init__(self, live: Live, session: requests.Session) -> None:
        super().__init__()
        self._init_for_debug(live.room_id)
        self._live = live
        self._session = session

    def __call__(self, source: Observable[str]) -> Observable[m3u8.M3U8]:
        return self._fetch(source)

    def _fetch(self, source: Observable[str]) -> Observable[m3u8.M3U8]:
        def subscribe(
            observer: abc.ObserverBase[m3u8.M3U8],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            if self._debug:
                path = '{}/playlist-{}-{}.m3u8'.format(
                    self._debug_dir,
                    self._live.room_id,
                    datetime.now().strftime('%Y-%m-%d-%H%M%S-%f'),
                )
                playlist_debug_file = open(path, 'wt', encoding='utf-8')

            disposed = False
            subscription = SerialDisposable()

            def on_next(url: str) -> None:
                logger.info(f'Fetching playlist... {url}')

                while not disposed:
                    try:
                        content = self._fetch_playlist(url)
                    except Exception as e:
                        logger.warning(f'Failed to fetch playlist: {repr(e)}')
                        observer.on_error(e)
                    else:
                        if self._debug:
                            playlist_debug_file.write(content + '\n')
                        playlist = m3u8.loads(content, uri=url)
                        if playlist.is_variant:
                            url = self._get_best_quality_url(playlist)
                            logger.debug('Playlist changed to variant playlist')
                            on_next(url)
                        else:
                            observer.on_next(playlist)
                            time.sleep(1)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                if self._debug:
                    playlist_debug_file.close()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    def _get_best_quality_url(self, playlist: m3u8.M3U8) -> str:
        sorted_playlists = sorted(
            playlist.playlists, key=lambda p: p.stream_info.bandwidth
        )
        return sorted_playlists[-1].absolute_uri

    @retry(
        reraise=True,
        retry=retry_if_exception_type(
            (
                requests.exceptions.Timeout,
                urllib3.exceptions.TimeoutError,
                urllib3.exceptions.ProtocolError,
            )
        ),
        wait=wait_exponential(multiplier=0.1, max=1),
        stop=stop_after_delay(8),
    )
    def _fetch_playlist(self, url: str) -> str:
        try:
            response = self._session.get(url, headers=self._live.headers, timeout=3)
            response.raise_for_status()
        except Exception as e:
            logger.debug(f'Failed to fetch playlist: {repr(e)}')
            raise
        else:
            response.encoding = 'utf-8'
            return response.text
