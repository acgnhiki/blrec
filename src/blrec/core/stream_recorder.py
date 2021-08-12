import io
import os
import time
import errno
import asyncio
import logging
from threading import Thread
from datetime import datetime, timezone, timedelta
from collections import OrderedDict

from typing import Any, BinaryIO, Dict, Iterator, Optional, Tuple

import aiohttp
import requests
import urllib3
from tqdm import tqdm
from rx.subject import Subject
from rx.core import Observable
from tenacity import (
    retry,
    wait_none,
    wait_fixed,
    wait_chain,
    wait_exponential,
    stop_after_delay,
    stop_after_attempt,
    retry_if_result,
    retry_if_exception,
    retry_if_exception_type,
    Retrying,
    TryAgain,
)

from .. import __version__, __prog__
from .retry import wait_exponential_for_same_exceptions, before_sleep_log
from .statistics import StatisticsCalculator
from ..event.event_emitter import EventListener, EventEmitter
from ..bili.live import Live
from ..bili.typing import QualityNumber
from ..flv.stream_processor import StreamProcessor, BaseOutputFileManager
from ..utils.mixins import AsyncCooperationMix, AsyncStoppableMixin
from ..flv.exceptions import FlvStreamCorruptedError
from ..bili.exceptions import (
    LiveRoomHidden, LiveRoomLocked, LiveRoomEncrypted, NoStreamUrlAvailable
)


__all__ = 'StreamRecorderEventListener', 'StreamRecorder'


logger = logging.getLogger(__name__)
logging.getLogger(urllib3.__name__).setLevel(logging.WARNING)


class StreamRecorderEventListener(EventListener):
    async def on_video_file_created(
        self, path: str, record_start_time: int
    ) -> None:
        ...

    async def on_video_file_completed(self, path: str) -> None:
        ...


class StreamRecorder(
    EventEmitter[StreamRecorderEventListener],
    AsyncCooperationMix,
    AsyncStoppableMixin,
):
    def __init__(
        self,
        live: Live,
        out_dir: str,
        path_template: str,
        *,
        quality_number: QualityNumber = 10000,
        buffer_size: Optional[int] = None,
        read_timeout: Optional[int] = None,
        filesize_limit: int = 0,
        duration_limit: int = 0,
    ) -> None:
        super().__init__()

        self._live = live
        self._progress_bar: Optional[tqdm] = None
        self._stream_processor: Optional[StreamProcessor] = None
        self._calculator = StatisticsCalculator()
        self._file_manager = OutputFileManager(
            live, out_dir, path_template, buffer_size
        )

        self._quality_number = quality_number
        self._real_quality_number: Optional[QualityNumber] = None
        self.buffer_size = buffer_size or io.DEFAULT_BUFFER_SIZE  # bytes
        self.read_timeout = read_timeout or 3  # seconds

        self._filesize_limit = filesize_limit or 0
        self._duration_limit = duration_limit or 0

        def on_file_created(args: Tuple[str, int]) -> None:
            logger.info(f"Video file created: '{args[0]}'")
            self._emit_event('video_file_created', *args)

        def on_file_closed(path: str) -> None:
            logger.info(f"Video file completed: '{path}'")
            self._emit_event('video_file_completed', path)

        self._file_manager.file_creates.subscribe(on_file_created)
        self._file_manager.file_closes.subscribe(on_file_closed)

    @property
    def data_count(self) -> int:
        return self._calculator.count

    @property
    def data_rate(self) -> float:
        return self._calculator.rate

    @property
    def elapsed(self) -> float:
        return self._calculator.elapsed

    @property
    def out_dir(self) -> str:
        return self._file_manager.out_dir

    @out_dir.setter
    def out_dir(self, value: str) -> None:
        self._file_manager.out_dir = value

    @property
    def path_template(self) -> str:
        return self._file_manager.path_template

    @path_template.setter
    def path_template(self, value: str) -> None:
        self._file_manager.path_template = value

    @property
    def quality_number(self) -> QualityNumber:
        return self._quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._quality_number = value
        self._real_quality_number = None

    @property
    def real_quality_number(self) -> QualityNumber:
        return self._real_quality_number or 10000

    @property
    def filesize_limit(self) -> int:
        if self._stream_processor is not None:
            return self._stream_processor.filesize_limit
        else:
            return self._filesize_limit

    @filesize_limit.setter
    def filesize_limit(self, value: int) -> None:
        self._filesize_limit = value
        if self._stream_processor is not None:
            self._stream_processor.filesize_limit = value

    @property
    def duration_limit(self) -> int:
        if self._stream_processor is not None:
            return self._stream_processor.duration_limit
        else:
            return self._duration_limit

    @duration_limit.setter
    def duration_limit(self, value: int) -> None:
        self._duration_limit = value
        if self._stream_processor is not None:
            self._stream_processor.duration_limit = value

    def has_file(self) -> bool:
        return self._file_manager.has_file()

    def get_files(self) -> Iterator[str]:
        yield from self._file_manager.get_files()

    def clear_files(self) -> None:
        self._file_manager.clear_files()

    def update_progress_bar_info(self) -> None:
        if self._progress_bar is not None:
            self._progress_bar.set_postfix_str(self._make_pbar_postfix())

    async def _do_start(self) -> None:
        self._thread = Thread(
            target=self._run, name=f'StreamRecorder::{self._live.room_id}'
        )
        self._thread.start()
        logger.debug('Started stream recorder')

    async def _do_stop(self) -> None:
        logger.debug('Stopping stream recorder...')
        if self._stream_processor is not None:
            self._stream_processor.cancel()
        await self._loop.run_in_executor(None, self._thread.join)
        logger.debug('Stopped stream recorder')

    def _run(self) -> None:
        self._calculator.reset()
        try:
            with tqdm(
                desc='Recording',
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                postfix=self._make_pbar_postfix(),
            ) as progress_bar:
                self._progress_bar = progress_bar

                def update_size(size: int) -> None:
                    progress_bar.update(size)
                    self._calculator.submit(size)

                self._stream_processor = StreamProcessor(
                    self._file_manager,
                    filesize_limit=self._filesize_limit,
                    duration_limit=self._duration_limit,
                    metadata=self._make_metadata(),
                    analyse_data=True,
                    dedup_join=True,
                    save_extra_metadata=True,
                )
                self._stream_processor.size_updates.subscribe(update_size)

                with requests.Session() as self._session:
                    self._main_loop()
        except TryAgain:
            pass
        except Exception as e:
            self._handle_exception(e)
        finally:
            if self._stream_processor is not None:
                self._stream_processor.finalize()
                self._stream_processor = None
            self._progress_bar = None
            self._calculator.freeze()

    def _main_loop(self) -> None:
        for attempt in Retrying(
            reraise=True,
            retry=(
                retry_if_result(lambda r: not self._stopped) |
                retry_if_exception(lambda e: not isinstance(e, OSError))
            ),
            wait=wait_exponential_for_same_exceptions(max=60),
            before_sleep=before_sleep_log(logger, logging.DEBUG, 'main_loop'),
        ):
            with attempt:
                try:
                    self._streaming_loop()
                except NoStreamUrlAvailable:
                    logger.debug('No stream url available')
                    if not self._stopped:
                        raise TryAgain
                except OSError as e:
                    if e.errno == errno.ENOSPC:
                        # OSError(28, 'No space left on device')
                        raise
                    logger.critical(repr(e), exc_info=e)
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
                    raise

    def _streaming_loop(self) -> None:
        url = self._get_live_stream_url()

        while not self._stopped:
            try:
                self._streaming(url)
            except requests.exceptions.HTTPError as e:
                # frequently occurred when the live just started or ended.
                logger.debug(repr(e))
                self._defer_retry(1, 'streaming_loop')
                # the url may has been forbidden or expired
                # when the status code is 404 or 403
                if e.response.status_code in (403, 404):
                    url = self._get_live_stream_url()
            except requests.exceptions.Timeout as e:
                logger.warning(repr(e))
            except urllib3.exceptions.TimeoutError as e:
                logger.warning(repr(e))
            except urllib3.exceptions.ProtocolError as e:
                # ProtocolError('Connection broken: IncompleteRead(
                logger.warning(repr(e))
            except requests.exceptions.ConnectionError as e:
                logger.warning(repr(e))
            except FlvStreamCorruptedError as e:
                logger.warning(repr(e))

    def _streaming(self, url: str) -> None:
        logger.debug('Getting the live stream...')
        with self._session.get(
            url,
            headers=self._live.headers,
            stream=True,
            timeout=self.read_timeout,
        ) as response:
            logger.debug('Response received')
            response.raise_for_status()

            assert self._stream_processor is not None
            self._stream_processor.process_stream(
                io.BufferedReader(
                    ResponseProxy(response.raw), buffer_size=8192
                )
            )

    @retry(
        reraise=True,
        retry=retry_if_exception_type((
            asyncio.TimeoutError, aiohttp.ClientError,
        )),
        wait=wait_chain(wait_none(), wait_fixed(1)),
        stop=stop_after_attempt(300),
    )
    def _get_live_stream_url(self) -> str:
        qn = self._real_quality_number or self.quality_number
        url = self._run_coroutine(self._live.get_live_stream_url(qn, 'flv'))

        if self._real_quality_number is None:
            if url is None:
                logger.info(
                    f'The specified video quality ({qn}) is not available, '
                    'using the original video quality (10000) instead.'
                )
                self._real_quality_number = 10000
                raise TryAgain
            else:
                logger.info(f'The specified video quality ({qn}) is available')
                self._real_quality_number = self.quality_number

        assert url is not None
        logger.debug(f"Got live stream url: '{url}'")

        return url

    def _defer_retry(self, seconds: float, name: str = '') -> None:
        if seconds <= 0:
            return
        logger.debug(f'Retry {name} after {seconds} seconds')
        time.sleep(seconds)

    def _make_pbar_postfix(self) -> str:
        return '{room_id} - {user_name}: {room_title}'.format(
            room_id=self._live.room_info.room_id,
            user_name=self._live.user_info.name,
            room_title=self._live.room_info.title,
        )

    def _make_metadata(self) -> Dict[str, Any]:
        github_url = 'https://github.com/acgnhiki/blrec'
        live_start_time = datetime.fromtimestamp(
            self._live.room_info.live_start_time, timezone(timedelta(hours=8))
        )

        return {
            'Title': self._live.room_info.title,
            'Artist': self._live.user_info.name,
            'Date': str(live_start_time),
            'Comment': f'''\
B站直播录像
主播：{self._live.user_info.name}
标题：{self._live.room_info.title}
分区：{self._live.room_info.parent_area_name} - {self._live.room_info.area_name}
房间号：{self._live.room_info.room_id}
开播时间：{live_start_time}
录制程序：{__prog__} v{__version__} {github_url}''',
            'description': OrderedDict({
                'UserId': str(self._live.user_info.uid),
                'UserName': self._live.user_info.name,
                'RoomId': str(self._live.room_info.room_id),
                'RoomTitle': self._live.room_info.title,
                'Area': self._live.room_info.area_name,
                'ParentArea': self._live.room_info.parent_area_name,
                'LiveStartTime': str(live_start_time),
                'Recorder': f'{__prog__} v{__version__} {github_url}',
            })
        }

    def _emit_event(self, name: str, *args: Any, **kwds: Any) -> None:
        self._run_coroutine(super()._emit(name, *args, **kwds))


class ResponseProxy(io.RawIOBase):
    def __init__(self, response: urllib3.HTTPResponse) -> None:
        self._response = response

    @property
    def closed(self) -> bool:
        # always return False to avoid that `ValueError: read of closed file`,
        # raised from `CHECK_CLOSED(self, "read of closed file")`,
        # result in losing data those remaining in the buffer.
        # ref: `https://gihub.com/python/cpython/blob/63298930fb531ba2bb4f23bc3b915dbf1e17e9e1/Modules/_io/bufferedio.c#L882`  # noqa
        return False

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        return self._response.read(size)

    def tell(self) -> int:
        return self._response.tell()

    def readinto(self, b: Any) -> int:
        return self._response.readinto(b)

    def close(self) -> None:
        self._response.close()


class OutputFileManager(BaseOutputFileManager, AsyncCooperationMix):
    def __init__(
        self,
        live: Live,
        out_dir: str,
        path_template: str,
        buffer_size: Optional[int] = None,
    ) -> None:
        super().__init__(buffer_size)
        self._live = live

        self.out_dir = out_dir
        self.path_template = path_template

        self._file_creates = Subject()
        self._file_closes = Subject()

    @property
    def file_creates(self) -> Observable:
        return self._file_creates

    @property
    def file_closes(self) -> Observable:
        return self._file_closes

    def create_file(self) -> BinaryIO:
        self._start_time = self._get_timestamp()
        file = super().create_file()
        self._file_creates.on_next((self._curr_path, self._start_time))
        return file

    def close_file(self) -> None:
        path = self._curr_path
        super().close_file()
        self._file_closes.on_next(path)

    def _get_timestamp(self) -> int:
        try:
            return self._get_server_timestamp()
        except Exception as e:
            logger.warning(f'Failed to get server timestamp: {repr(e)}')
            return self._get_local_timestamp()

    def _get_local_timestamp(self) -> int:
        return int(time.time())

    @retry(
        reraise=True,
        retry=retry_if_exception_type((
            asyncio.TimeoutError, aiohttp.ClientError,
        )),
        wait=wait_exponential(multiplier=0.1, max=1),
        stop=stop_after_delay(3),
    )
    def _get_server_timestamp(self) -> int:
        return self._run_coroutine(self._live.get_server_timestamp())

    def _make_path(self) -> str:
        date_time = datetime.fromtimestamp(self._start_time)
        relpath = self.path_template.format(
            roomid=self._live.room_id,
            uname=self._live.user_info.name,
            title=self._live.room_info.title,
            area=self._live.room_info.area_name,
            parent_area=self._live.room_info.parent_area_name,
            year=date_time.year,
            month=str(date_time.month).rjust(2, '0'),
            day=str(date_time.day).rjust(2, '0'),
            hour=str(date_time.hour).rjust(2, '0'),
            minute=str(date_time.minute).rjust(2, '0'),
            second=str(date_time.second).rjust(2, '0'),
        )

        full_pathname = os.path.abspath(
            os.path.expanduser(os.path.join(self.out_dir, relpath) + '.flv')
        )
        os.makedirs(os.path.dirname(full_pathname), exist_ok=True)

        return full_pathname
