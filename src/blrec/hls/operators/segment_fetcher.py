from __future__ import annotations

import logging
import time
from typing import Optional, Union

import attr
import m3u8
import requests
import urllib3
from m3u8.model import InitializationSection
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_exponential

from blrec.bili.live import Live
from blrec.utils.hash import cksum

from ..exceptions import SegmentDataCorrupted

__all__ = ('SegmentFetcher', 'InitSectionData', 'SegmentData')


logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class InitSectionData:
    init_section: InitializationSection
    payload: bytes

    def __len__(self) -> int:
        return len(self.payload)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class SegmentData:
    segment: m3u8.Segment
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

            last_segment: Optional[m3u8.Segment] = None

            def on_next(seg: m3u8.Segment) -> None:
                nonlocal last_segment
                url: str = ''

                try:
                    if hasattr(seg, 'init_section') and (
                        (
                            last_segment is None
                            or seg.init_section != last_segment.init_section
                            or seg.discontinuity
                        )
                    ):
                        url = seg.init_section.absolute_uri
                        data = self._fetch_segment(url)
                        while True:
                            time.sleep(1)
                            if (_data := self._fetch_segment(url)) == data:
                                logger.debug(
                                    'Init section checked: '
                                    f'crc32 of previous data: {cksum(data)}, '
                                    f'crc32 of current data: {cksum(_data)}, '
                                    f'init section url: {url}'
                                )
                                break
                            else:
                                logger.debug(
                                    'Init section corrupted: '
                                    f'crc32 of previous data: {cksum(data)}, '
                                    f'crc32 of current data: {cksum(_data)}, '
                                    f'init section url: {url}'
                                )
                                data = _data
                        observer.on_next(
                            InitSectionData(init_section=seg.init_section, payload=data)
                        )
                    last_segment = seg

                    url = seg.absolute_uri
                    crc32 = seg.title.split('|')[-1]
                    for _ in range(3):
                        data = self._fetch_segment(url)
                        crc32_of_data = cksum(data)
                        if crc32_of_data == crc32:
                            break
                        logger.debug(
                            'Segment data corrupted: '
                            f'correct crc32: {crc32}, '
                            f'crc32 of segment data: {crc32_of_data}, '
                            f'segment url: {url}'
                        )
                    else:
                        raise SegmentDataCorrupted(crc32, crc32_of_data)
                except Exception as exc:
                    logger.warning(f'Failed to fetch segment {url}', exc_info=exc)
                else:
                    observer.on_next(SegmentData(segment=seg, payload=data))

            def dispose() -> None:
                nonlocal disposed
                nonlocal last_segment
                disposed = True
                last_segment = None

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    @retry(
        reraise=True,
        retry=retry_if_exception_type(
            (requests.exceptions.RequestException, urllib3.exceptions.HTTPError)
        ),
        wait=wait_exponential(max=10),
        stop=stop_after_delay(60),
    )
    def _fetch_segment(self, url: str) -> bytes:
        with self._session.get(url, headers=self._live.headers, timeout=10) as response:
            response.raise_for_status()
            return response.content
