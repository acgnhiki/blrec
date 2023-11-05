from __future__ import annotations

import io
from typing import Optional

import requests
from loguru import logger
from reactivex import Observable, abc

from blrec.bili.live import Live
from blrec.utils.mixins import AsyncCooperationMixin

__all__ = ('StreamFetcher',)


class StreamFetcher(AsyncCooperationMixin):
    def __init__(
        self,
        live: Live,
        session: requests.Session,
        *,
        read_timeout: Optional[int] = None,
    ) -> None:
        super().__init__()
        self._live = live
        self._session = session
        self.read_timeout = read_timeout or 3

    def __call__(self, source: Observable[str]) -> Observable[io.RawIOBase]:
        return self._fetch(source)

    def _fetch(self, source: Observable[str]) -> Observable[io.RawIOBase]:
        def subscribe(
            observer: abc.ObserverBase[io.RawIOBase],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            def on_next(url: str) -> None:
                try:
                    logger.info(f'Requesting live stream... {url}')
                    response = self._session.get(
                        url,
                        stream=True,
                        headers=self._live.headers,
                        timeout=self.read_timeout,
                    )
                    logger.info('Response received')
                    response.raise_for_status()
                except Exception as e:
                    logger.warning(f'Failed to request live stream: {repr(e)}')
                    observer.on_error(e)
                else:
                    observer.on_next(response.raw)  # urllib3.response.HTTPResponse

            return source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)
