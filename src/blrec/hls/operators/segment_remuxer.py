from __future__ import annotations

import io
import logging
from typing import Final, List, Optional, Union

import urllib3
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from tenacity import Retrying, stop_after_delay, wait_fixed
from tenacity.retry import retry_if_not_exception_type

from blrec.bili.live import Live
from blrec.utils.io import wait_for

from ..stream_remuxer import StreamRemuxer
from .segment_fetcher import InitSectionData, SegmentData

__all__ = ('SegmentRemuxer',)


logger = logging.getLogger(__name__)
logging.getLogger(urllib3.__name__).setLevel(logging.WARNING)


class SegmentRemuxer:
    _SEGMENT_DATA_CACHE: Final = 10
    _MAX_SEGMENT_DATA_CACHE: Final = 15

    def __init__(self, live: Live) -> None:
        self._live = live
        self._timeout: float = 10
        self._stream_remuxer = StreamRemuxer(live.room_id, remove_filler_data=True)

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[io.RawIOBase]:
        return self._remux(source)

    def _remux(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[io.RawIOBase]:
        def subscribe(
            observer: abc.ObserverBase[io.RawIOBase],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            init_section_data: Optional[bytes] = None
            segment_data_cache: List[bytes] = []
            self._stream_remuxer.stop()

            def reset() -> None:
                nonlocal init_section_data, segment_data_cache
                init_section_data = None
                segment_data_cache = []
                self._stream_remuxer.stop()

            def write(data: bytes) -> int:
                return wait_for(
                    self._stream_remuxer.input.write,
                    args=(data,),
                    timeout=self._timeout,
                )

            def on_next(data: Union[InitSectionData, SegmentData]) -> None:
                nonlocal init_section_data
                nonlocal segment_data_cache

                if isinstance(data, InitSectionData):
                    init_section_data = data.payload
                    segment_data_cache.clear()
                    logger.debug('Stop stream remuxer for init section')
                    self._stream_remuxer.stop()

                if self._stream_remuxer.exception and not self._stream_remuxer.stopped:
                    logger.debug(
                        'Stop stream remuxer due to '
                        + repr(self._stream_remuxer.exception)
                    )
                    self._stream_remuxer.stop()

                try:
                    if self._stream_remuxer.stopped:
                        self._stream_remuxer.start()
                        while True:
                            ready = self._stream_remuxer.wait(timeout=1)
                            if disposed:
                                return
                            if ready:
                                break

                        observer.on_next(RemuxedStream(self._stream_remuxer))

                        if init_section_data:
                            write(init_section_data)
                        if segment_data_cache:
                            for cached_data in segment_data_cache:
                                write(cached_data)
                        if isinstance(data, InitSectionData):
                            return

                    write(data.payload)
                except Exception as e:
                    logger.warning(f'Failed to write data to stream remuxer: {repr(e)}')
                    logger.debug(f'Stop stream remuxer due to {repr(e)}')
                    self._stream_remuxer.stop()
                    if len(segment_data_cache) >= self._MAX_SEGMENT_DATA_CACHE:
                        segment_data_cache = segment_data_cache[
                            -self._MAX_SEGMENT_DATA_CACHE + 1 :
                        ]
                else:
                    if len(segment_data_cache) >= self._SEGMENT_DATA_CACHE:
                        segment_data_cache = segment_data_cache[
                            -self._SEGMENT_DATA_CACHE + 1 :
                        ]

                segment_data_cache.append(data.payload)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                reset()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)


class CloseRemuxedStream(Exception):
    pass


class RemuxedStream(io.RawIOBase):
    def __init__(
        self, stream_remuxer: StreamRemuxer, *, read_timeout: float = 10
    ) -> None:
        self._stream_remuxer = stream_remuxer
        self._read_timeout = read_timeout
        self._offset: int = 0

    def read(self, size: int = -1) -> bytes:
        if self._stream_remuxer.stopped:
            ready = self._stream_remuxer.wait(timeout=self._read_timeout)
            if not ready:
                msg = f'Stream remuxer not ready in {self._read_timeout} seconds'
                logger.debug(msg)
                raise EOFError(msg)

        try:
            for attempt in Retrying(
                reraise=True,
                retry=retry_if_not_exception_type(TimeoutError),
                wait=wait_fixed(1),
                stop=stop_after_delay(self._read_timeout),
            ):
                with attempt:
                    data = wait_for(
                        self._stream_remuxer.output.read,
                        args=(size,),
                        timeout=self._read_timeout,
                    )
        except Exception as exc:
            logger.warning(f'Failed to read data from stream remuxer: {repr(exc)}')
            self._stream_remuxer.exception = exc
            raise EOFError(exc)
        else:
            assert data is not None
            self._offset += len(data)
            return data

    def tell(self) -> int:
        return self._offset

    def close(self) -> None:
        if self._stream_remuxer.stopped:
            return
        if self._stream_remuxer.exception:
            return
        logger.debug('Close remuxed stream')
        self._stream_remuxer.exception = CloseRemuxedStream()
