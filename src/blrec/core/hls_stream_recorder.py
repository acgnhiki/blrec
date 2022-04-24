import io
import time
import errno
import logging
from queue import Queue, Empty
from threading import Thread, Event, Lock, Condition
from datetime import datetime
from contextlib import suppress
from urllib.parse import urlparse

from typing import List, Set, Optional

import urllib3
import requests
import m3u8
from m3u8.model import Segment
from tqdm import tqdm
from tenacity import (
    retry,
    wait_exponential,
    stop_after_delay,
    retry_if_result,
    retry_if_exception_type,
    retry_if_not_exception_type,
    Retrying,
    TryAgain,
    RetryError,
)

from .stream_remuxer import StreamRemuxer
from .stream_analyzer import ffprobe, StreamProfile
from .base_stream_recorder import BaseStreamRecorder, StreamProxy
from .exceptions import FailedToFetchSegments
from .retry import wait_exponential_for_same_exceptions, before_sleep_log
from ..bili.live import Live
from ..bili.typing import StreamFormat, QualityNumber
from ..flv.stream_processor import StreamProcessor
from ..flv.exceptions import FlvDataError, FlvStreamCorruptedError
from ..utils.mixins import (
    AsyncCooperationMixin, AsyncStoppableMixin, SupportDebugMixin
)
from ..bili.exceptions import (
    LiveRoomHidden, LiveRoomLocked, LiveRoomEncrypted, NoStreamAvailable,
)


__all__ = 'HLSStreamRecorder',


logger = logging.getLogger(__name__)


class HLSStreamRecorder(
    BaseStreamRecorder,
    AsyncCooperationMixin,
    AsyncStoppableMixin,
    SupportDebugMixin,
):
    def __init__(
        self,
        live: Live,
        out_dir: str,
        path_template: str,
        *,
        stream_format: StreamFormat = 'flv',
        quality_number: QualityNumber = 10000,
        buffer_size: Optional[int] = None,
        read_timeout: Optional[int] = None,
        disconnection_timeout: Optional[int] = None,
        filesize_limit: int = 0,
        duration_limit: int = 0,
    ) -> None:
        super().__init__(
            live=live,
            out_dir=out_dir,
            path_template=path_template,
            stream_format=stream_format,
            quality_number=quality_number,
            buffer_size=buffer_size,
            read_timeout=read_timeout,
            disconnection_timeout=disconnection_timeout,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )
        self._init_for_debug(self._live.room_id)
        self._init_section_data: Optional[bytes] = None
        self._ready_to_fetch_segments = Condition()
        self._failed_to_fetch_segments = Event()
        self._stream_analysed_lock = Lock()
        self._last_segment_uris: Set[str] = set()

    def _run(self) -> None:
        logger.debug('Stream recorder thread started')
        try:
            if self._debug:
                path = '{}/playlist-{}-{}.m3u8'.format(
                    self._debug_dir,
                    self._live.room_id,
                    datetime.now().strftime('%Y-%m-%d-%H%M%S-%f'),
                )
                self._playlist_debug_file = open(path, 'wt', encoding='utf-8')

            self._session = requests.Session()
            self._session.headers.update(self._live.headers)

            self._stream_remuxer = StreamRemuxer(self._live.room_id)
            self._segment_queue: Queue[Segment] = Queue(maxsize=1000)
            self._segment_data_queue: Queue[bytes] = Queue(maxsize=100)
            self._stream_host_available = Event()

            self._segment_fetcher_thread = Thread(
                target=self._run_segment_fetcher,
                name=f'SegmentFetcher::{self._live.room_id}',
                daemon=True,
            )
            self._segment_fetcher_thread.start()

            self._segment_data_feeder_thread = Thread(
                target=self._run_segment_data_feeder,
                name=f'SegmentDataFeeder::{self._live.room_id}',
                daemon=True,
            )
            self._segment_data_feeder_thread.start()

            self._stream_processor_thread = Thread(
                target=self._run_stream_processor,
                name=f'StreamProcessor::{self._live.room_id}',
                daemon=True,
            )
            self._stream_processor_thread.start()

            try:
                self._main_loop()
            finally:
                if self._stream_processor is not None:
                    self._stream_processor.cancel()
                self._stream_processor_thread.join(timeout=10)
                self._segment_fetcher_thread.join(timeout=10)
                self._segment_data_feeder_thread.join(timeout=10)
                self._stream_remuxer.stop()
                self._stream_remuxer.raise_for_exception()
                self._last_segment_uris.clear()
                del self._segment_queue
                del self._segment_data_queue
        except TryAgain:
            pass
        except Exception as e:
            self._handle_exception(e)
        finally:
            self._stopped = True
            with suppress(Exception):
                self._playlist_debug_file.close()
            self._emit_event('stream_recording_stopped')
            logger.debug('Stream recorder thread stopped')

    def _main_loop(self) -> None:
        for attempt in Retrying(
            reraise=True,
            retry=(
                retry_if_result(lambda r: not self._stopped) |
                retry_if_not_exception_type((OSError, NotImplementedError))
            ),
            wait=wait_exponential_for_same_exceptions(max=60),
            before_sleep=before_sleep_log(logger, logging.DEBUG, 'main_loop'),
        ):
            with attempt:
                try:
                    self._streaming_loop()
                except NoStreamAvailable as e:
                    logger.warning(f'No stream available: {repr(e)}')
                    if not self._stopped:
                        raise TryAgain
                except OSError as e:
                    logger.critical(repr(e), exc_info=e)
                    if e.errno == errno.ENOSPC:
                        # OSError(28, 'No space left on device')
                        self._handle_exception(e)
                        self._stopped = True
                    raise TryAgain
                except LiveRoomHidden:
                    logger.error('The live room has been hidden!')
                    self._stopped = True
                except LiveRoomLocked:
                    logger.error('The live room has been locked!')
                    self._stopped = True
                except LiveRoomEncrypted:
                    logger.error('The live room has been encrypted!')
                    self._stopped = True
                except Exception as e:
                    logger.exception(e)
                    self._handle_exception(e)
                    self._stopped = True

    def _streaming_loop(self) -> None:
        url = self._get_live_stream_url()

        while not self._stopped:
            try:
                self._playlist_fetcher(url)
            except requests.exceptions.HTTPError as e:
                # frequently occurred when the live just started or ended.
                logger.warning(repr(e))
                self._defer_retry(1, 'streaming_loop')
                # the url may has been forbidden or expired
                # when the status code is 404 or 403
                if e.response.status_code in (403, 404):
                    url = self._get_live_stream_url()
            except requests.exceptions.ConnectionError as e:
                logger.warning(repr(e))
                self._wait_for_connection_error()
            except FailedToFetchSegments:
                url = self._get_live_stream_url()
            except RetryError as e:
                logger.warning(repr(e))

    def _playlist_fetcher(self, url: str) -> None:
        self._stream_url = url
        self._stream_host = urlparse(url).hostname or ''
        self._stream_host_available.set()
        with self._stream_analysed_lock:
            self._stream_analysed = False

        while not self._stopped:
            if self._failed_to_fetch_segments.is_set():
                with self._segment_queue.mutex:
                    self._segment_queue.queue.clear()
                with self._ready_to_fetch_segments:
                    self._ready_to_fetch_segments.notify_all()
                self._failed_to_fetch_segments.clear()
                raise FailedToFetchSegments()

            content = self._fetch_playlist(url)
            playlist = m3u8.loads(content, uri=url)

            if self._debug:
                self._playlist_debug_file.write(content + '\n')

            if playlist.is_variant:
                url = sorted(
                    playlist.playlists,
                    key=lambda p: p.stream_info.bandwidth
                )[-1].absolute_uri
                logger.debug(f'playlist changed to variant playlist: {url}')
                self._stream_url = url
                self._stream_host = urlparse(url).hostname or ''
                with self._stream_analysed_lock:
                    self._stream_analysed = False
                continue

            uris: Set[str] = set()
            for seg in playlist.segments:
                uris.add(seg.uri)
                if seg.uri not in self._last_segment_uris:
                    self._segment_queue.put(seg, timeout=60)

            if (
                self._last_segment_uris and
                not uris.intersection(self._last_segment_uris)
            ):
                logger.debug(
                    'segments broken!\n'
                    f'last segments: {self._last_segment_uris}\n'
                    f'current segments: {uris}'
                )
                with self._stream_analysed_lock:
                    self._stream_analysed = False

            self._last_segment_uris = uris

            if playlist.is_endlist:
                logger.debug('playlist ended')
                self._run_coroutine(self._live.update_room_info())
                if not self._live.is_living():
                    self._stopped = True
                    break

            time.sleep(1)

    def _run_segment_fetcher(self) -> None:
        logger.debug('Segment fetcher thread started')
        try:
            self._segment_fetcher()
        except Exception as e:
            logger.exception(e)
            self._handle_exception(e)
        finally:
            self._dl_calculator.freeze()
            logger.debug('Segment fetcher thread stopped')

    def _segment_fetcher(self) -> None:
        assert self._stream_remuxer is not None
        init_section = None
        self._init_section_data = None
        num_of_continuously_failed = 0
        self._failed_to_fetch_segments.clear()

        while not self._stopped:
            try:
                seg = self._segment_queue.get(timeout=1)
            except Empty:
                continue
            for attempt in Retrying(
                reraise=True,
                retry=(
                    retry_if_result(lambda r: not self._stopped) |
                    retry_if_not_exception_type((OSError, NotImplementedError))
                ),
            ):
                if attempt.retry_state.attempt_number > 3:
                    break
                with attempt:
                    try:
                        if (
                            getattr(seg, 'init_section', None) and
                            (
                                not init_section or
                                seg.init_section.uri != init_section.uri
                            )
                        ):
                            data = self._fetch_segment(
                                seg.init_section.absolute_uri
                            )
                            init_section = seg.init_section
                            self._init_section_data = data
                            self._segment_data_queue.put(data, timeout=60)
                        data = self._fetch_segment(seg.absolute_uri)
                        self._segment_data_queue.put(data, timeout=60)
                    except requests.exceptions.HTTPError as e:
                        logger.warning(f'Failed to fetch segment: {repr(e)}')
                        if e.response.status_code in (403, 404, 599):
                            num_of_continuously_failed += 1
                            if num_of_continuously_failed >= 3:
                                self._failed_to_fetch_segments.set()
                                with self._ready_to_fetch_segments:
                                    self._ready_to_fetch_segments.wait()
                                    num_of_continuously_failed = 0
                                    self._failed_to_fetch_segments.clear()
                            break
                    except requests.exceptions.ConnectionError as e:
                        logger.warning(repr(e))
                        self._connection_recovered.wait()
                    except RetryError as e:
                        logger.warning(repr(e))
                        break
                    else:
                        num_of_continuously_failed = 0
                        break

    def _run_segment_data_feeder(self) -> None:
        logger.debug('Segment data feeder thread started')
        try:
            self._segment_data_feeder()
        except Exception as e:
            logger.exception(e)
            self._handle_exception(e)
        finally:
            logger.debug('Segment data feeder thread stopped')

    def _segment_data_feeder(self) -> None:
        assert self._stream_remuxer is not None
        MAX_SEGMENT_DATA_CACHE = 3
        segment_data_cache: List[bytes] = []
        bytes_io = io.BytesIO()
        segment_count = 0

        def on_next(profile: StreamProfile) -> None:
            self._stream_profile = profile

        def on_error(e: Exception) -> None:
            logger.warning(f'Failed to analyse stream: {repr(e)}')

        while not self._stopped:
            try:
                data = self._segment_data_queue.get(timeout=1)
            except Empty:
                continue
            else:
                with self._stream_analysed_lock:
                    if not self._stream_analysed:
                        if self._init_section_data and not bytes_io.getvalue():
                            bytes_io.write(self._init_section_data)
                        else:
                            bytes_io.write(data)
                            segment_count += 1

                        if segment_count >= 3:
                            ffprobe(bytes_io.getvalue()).subscribe(
                                on_next, on_error
                            )
                            bytes_io = io.BytesIO()
                            segment_count = 0
                            self._stream_analysed = True

            try:
                if self._stream_remuxer.stopped:
                    self._stream_remuxer.start()
                    while True:
                        ready = self._stream_remuxer.wait(timeout=1)
                        if self._stopped:
                            return
                        if ready:
                            break
                    if segment_data_cache:
                        if self._init_section_data:
                            self._stream_remuxer.input.write(
                                self._init_section_data
                            )
                        for cached_data in segment_data_cache:
                            if cached_data == self._init_section_data:
                                continue
                            self._stream_remuxer.input.write(cached_data)

                self._stream_remuxer.input.write(data)
            except BrokenPipeError as e:
                if not self._stopped:
                    logger.warning(repr(e))
                else:
                    logger.debug(repr(e))
            except ValueError as e:
                if not self._stopped:
                    logger.warning(repr(e))
                else:
                    logger.debug(repr(e))

            segment_data_cache.append(data)
            if len(segment_data_cache) > MAX_SEGMENT_DATA_CACHE:
                segment_data_cache.pop(0)

    def _run_stream_processor(self) -> None:
        logger.debug('Stream processor thread started')
        assert self._stream_remuxer is not None

        with tqdm(
            desc='Recording',
            unit='B',
            unit_scale=True,
            postfix=self._make_pbar_postfix(),
        ) as progress_bar:
            self._progress_bar = progress_bar

            def update_size(size: int) -> None:
                progress_bar.update(size)
                self._rec_calculator.submit(size)

            self._stream_processor = StreamProcessor(
                self._file_manager,
                filesize_limit=self._filesize_limit,
                duration_limit=self._duration_limit,
                analyse_data=True,
                dedup_join=True,
                save_extra_metadata=True,
                backup_timestamp=True,
            )
            self._stream_processor.size_updates.subscribe(update_size)

            try:
                while not self._stopped:
                    while True:
                        ready = self._stream_remuxer.wait(timeout=1)
                        if self._stopped:
                            return
                        if ready:
                            break

                    self._stream_host_available.wait()
                    self._stream_processor.set_metadata(self._make_metadata())

                    try:
                        self._stream_processor.process_stream(
                            StreamProxy(
                                self._stream_remuxer.output,
                                read_timeout=10,
                            )  # type: ignore
                        )
                    except BrokenPipeError as e:
                        logger.debug(repr(e))
                    except TimeoutError as e:
                        logger.debug(repr(e))
                        self._stream_remuxer.stop()
                    except FlvDataError as e:
                        logger.warning(repr(e))
                        self._stream_remuxer.stop()
                    except FlvStreamCorruptedError as e:
                        logger.warning(repr(e))
                        self._stream_remuxer.stop()
                    except ValueError as e:
                        logger.warning(repr(e))
                        self._stream_remuxer.stop()
            except Exception as e:
                if not self._stopped:
                    logger.exception(e)
                    self._handle_exception(e)
                else:
                    logger.debug(repr(e))
            finally:
                self._stream_processor.finalize()
                self._progress_bar = None
                self._rec_calculator.freeze()
                logger.debug('Stream processor thread stopped')

    @retry(
        retry=retry_if_exception_type((
            requests.exceptions.Timeout,
            urllib3.exceptions.TimeoutError,
            urllib3.exceptions.ProtocolError,
        )),
        wait=wait_exponential(multiplier=0.1, max=1),
        stop=stop_after_delay(10),
    )
    def _fetch_playlist(self, url: str) -> str:
        response = self._session.get(url, timeout=3)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text

    @retry(
        retry=retry_if_exception_type((
            requests.exceptions.Timeout,
            urllib3.exceptions.TimeoutError,
            urllib3.exceptions.ProtocolError,
        )),
        wait=wait_exponential(multiplier=0.1, max=5),
        stop=stop_after_delay(60),
    )
    def _fetch_segment(self, url: str) -> bytes:
        with self._session.get(url, stream=True, timeout=10) as response:
            response.raise_for_status()

            bytes_io = io.BytesIO()
            for chunk in response:
                bytes_io.write(chunk)
                self._dl_calculator.submit(len(chunk))

            return bytes_io.getvalue()
