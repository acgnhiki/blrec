from __future__ import annotations

import logging
from typing import Optional, Union

import attr
import m3u8
import requests
import urllib3
from m3u8.model import InitializationSection
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_exponential

from ...bili.live import Live

__all__ = ('SegmentFetcher', 'InitSectionData', 'SegmentData')


logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class InitSectionData:
    payload: bytes

    def __len__(self) -> int:
        return len(self.payload)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class SegmentData:
    payload: bytes

    def __len__(self) -> int:
        return len(self.payload)


class SegmentFetcher:
    def __init__(self, live: Live, session: requests.Session) -> None:
        self._live = live
        self._session = session

    def __call__(
        self, source: Observable[m3u8.Segment]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._fetch(source)

    def _fetch(
        self, source: Observable[m3u8.Segment]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        def subscribe(
            observer: abc.ObserverBase[Union[InitSectionData, SegmentData]],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            init_section: Optional[InitializationSection] = None

            def on_next(seg: m3u8.Segment) -> None:
                nonlocal init_section
                url: str = ''
                try:
                    if getattr(seg, 'init_section', None) and (
                        not init_section or seg.init_section.uri != init_section.uri
                    ):
                        url = seg.init_section.absolute_uri
                        data = self._fetch_segment(url)
                        init_section = seg.init_section
                        observer.on_next(InitSectionData(payload=data))
                    url = seg.absolute_uri
                    data = self._fetch_segment(url)
                    observer.on_next(SegmentData(payload=data))
                except Exception as e:
                    logger.warning(f'Failed to fetch segment {url}: {repr(e)}')

            def dispose() -> None:
                nonlocal disposed
                nonlocal init_section
                disposed = True
                init_section = None

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    @retry(
        reraise=True,
        retry=retry_if_exception_type(
            (
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError,
                urllib3.exceptions.TimeoutError,
                urllib3.exceptions.ProtocolError,
            )
        ),
        wait=wait_exponential(multiplier=0.1, max=5),
        stop=stop_after_delay(60),
    )
    def _fetch_segment(self, url: str) -> bytes:
        with self._session.get(url, headers=self._live.headers, timeout=10) as response:
            response.raise_for_status()
            return response.content
