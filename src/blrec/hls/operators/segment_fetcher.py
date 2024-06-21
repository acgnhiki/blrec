from __future__ import annotations

import time
from typing import Optional, Union

import attr
import m3u8
import requests
import urllib3
from loguru import logger
from reactivex import Observable, abc
from reactivex import operators as ops
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from tenacity import (
    retry,
    retry_all,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_delay,
    wait_exponential,
)

from blrec.bili.live import Live
from blrec.core import operators as core_ops
from blrec.utils import operators as utils_ops
from blrec.utils.hash import cksum
from blrec.exception.helpers import format_exception

from ..exceptions import FetchSegmentError, SegmentDataCorrupted

__all__ = ('SegmentFetcher', 'InitSectionData', 'SegmentData')


@attr.s(auto_attribs=True, slots=True, frozen=True)
class InitSectionData:
    segment: m3u8.Segment
    payload: bytes
    offset: int = 0

    def __len__(self) -> int:
        return len(self.payload)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class SegmentData:
    segment: m3u8.Segment
    payload: bytes
    offset: int = 0

    def __len__(self) -> int:
        return len(self.payload)


class SegmentFetcher:
    def __init__(
        self,
        live: Live,
        session: requests.Session,
        stream_url_resolver: core_ops.StreamURLResolver,
    ) -> None:
        self._live = live
        self._session = session
        self._stream_url_resolver = stream_url_resolver

    def __call__(
        self, source: Observable[m3u8.Segment]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._fetch(source).pipe(  # type: ignore
            ops.do_action(on_error=self._before_retry),
            utils_ops.retry(should_retry=self._should_retry),
        )

    def _fetch(
        self, source: Observable[m3u8.Segment]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        def subscribe(
            observer: abc.ObserverBase[Union[InitSectionData, SegmentData]],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            attempts: int = 0
            last_segment: Optional[m3u8.Segment] = None

            def on_next(seg: m3u8.Segment) -> None:
                nonlocal attempts, last_segment
                url: str = ''

                try:
                    if hasattr(seg, 'init_section') and (
                        (
                            last_segment is None
                            or seg.init_section != last_segment.init_section
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
                        observer.on_next(InitSectionData(segment=seg, payload=data))
                    last_segment = seg

                    url = seg.absolute_uri
                    hex_size, crc32, *_ = seg.title.split('|')
                    size = int(hex_size, 16)
                    for _ in range(3):
                        data = self._fetch_segment(url)
                        if len(data) != size:
                            logger.debug(
                                'Segment data incomplete: '
                                f'size expected: {size}, '
                                f'size fetched: {len(data)}, '
                                f'segment url: {url}'
                            )
                            continue
                        crc32_of_data = cksum(data)
                        if crc32_of_data != crc32:
                            logger.debug(
                                'Segment data corrupted: '
                                f'correct crc32: {crc32}, '
                                f'crc32 of segment data: {crc32_of_data}, '
                                f'segment url: {url}'
                            )
                            continue
                        break
                    else:
                        raise SegmentDataCorrupted(url)
                except Exception as exc:
                    logger.warning(
                        'Failed to fetch segment: {}\n{}', url, format_exception(exc)
                    )
                    attempts += 1
                    if attempts > 3:
                        attempts = 0
                        observer.on_error(FetchSegmentError(exc))
                else:
                    observer.on_next(SegmentData(segment=seg, payload=data))
                    attempts = 0

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
        retry=retry_all(
            retry_if_exception_type(
                (requests.exceptions.RequestException, urllib3.exceptions.HTTPError)
            ),
            retry_if_not_exception_type(requests.exceptions.HTTPError),
        ),
        wait=wait_exponential(max=10),
        stop=stop_after_delay(60),
    )
    def _fetch_segment(self, url: str) -> bytes:
        try:
            response = self._session.get(url, headers=self._live.headers, timeout=5)
            response.raise_for_status()
        except Exception as e:
            logger.debug(f'Failed to fetch segment {url}: {repr(e)}')
            raise
        else:
            return response.content

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, FetchSegmentError):
            return True
        else:
            return False

    def _before_retry(self, exc: Exception) -> None:
        if not isinstance(exc, FetchSegmentError):
            return
        logger.warning(
            'Fetch segments failed continuously, trying to update the stream url.'
        )
        self._stream_url_resolver.reset()
        self._stream_url_resolver.rotate_routes()
