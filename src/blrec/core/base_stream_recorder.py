import io
import os
import re
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from threading import Thread, Event
from datetime import datetime, timezone, timedelta
from collections import OrderedDict

from typing import Any, BinaryIO, Dict, Iterator, Optional, Tuple

import aiohttp
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
    retry_if_exception_type,
    TryAgain,
)

from .. import __version__, __prog__, __github__
from .stream_remuxer import StreamRemuxer
from .stream_analyzer import StreamProfile
from .statistics import StatisticsCalculator
from ..event.event_emitter import EventListener, EventEmitter
from ..bili.live import Live
from ..bili.typing import ApiPlatform, StreamFormat, QualityNumber
from ..bili.helpers import get_quality_name
from ..flv.data_analyser import MetaData
from ..flv.stream_processor import StreamProcessor, BaseOutputFileManager
from ..utils.io import wait_for
from ..utils.mixins import AsyncCooperationMixin, AsyncStoppableMixin
from ..path import escape_path
from ..logging.room_id import aio_task_with_room_id
from ..bili.exceptions import (
    NoStreamFormatAvailable, NoStreamCodecAvailable, NoStreamQualityAvailable,
)


__all__ = 'BaseStreamRecorder', 'StreamRecorderEventListener', 'StreamProxy'


logger = logging.getLogger(__name__)
logging.getLogger(urllib3.__name__).setLevel(logging.WARNING)


class StreamRecorderEventListener(EventListener):
    async def on_video_file_created(
        self, path: str, record_start_time: int
    ) -> None:
        ...

    async def on_video_file_completed(self, path: str) -> None:
        ...

    async def on_stream_recording_stopped(self) -> None:
        ...


class BaseStreamRecorder(
    EventEmitter[StreamRecorderEventListener],
    AsyncCooperationMixin,
    AsyncStoppableMixin,
    ABC,
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
        super().__init__()

        self._live = live
        self._progress_bar: Optional[tqdm] = None
        self._stream_remuxer: Optional[StreamRemuxer] = None
        self._stream_processor: Optional[StreamProcessor] = None
        self._dl_calculator = StatisticsCalculator()
        self._rec_calculator = StatisticsCalculator()
        self._file_manager = OutputFileManager(
            live, out_dir, path_template, buffer_size
        )

        self._stream_format = stream_format
        self._quality_number = quality_number
        self._real_stream_format: Optional[StreamFormat] = None
        self._real_quality_number: Optional[QualityNumber] = None
        self._api_platform: ApiPlatform = 'android'
        self._use_alternative_stream: bool = False
        self.buffer_size = buffer_size or io.DEFAULT_BUFFER_SIZE  # bytes
        self.read_timeout = read_timeout or 3  # seconds
        self.disconnection_timeout = disconnection_timeout or 600  # seconds

        self._filesize_limit = filesize_limit or 0
        self._duration_limit = duration_limit or 0

        self._stream_url: str = ''
        self._stream_host: str = ''
        self._stream_profile: StreamProfile = {}

        self._connection_recovered = Event()

        def on_file_created(args: Tuple[str, int]) -> None:
            logger.info(f"Video file created: '{args[0]}'")
            self._emit_event('video_file_created', *args)

        def on_file_closed(path: str) -> None:
            logger.info(f"Video file completed: '{path}'")
            self._emit_event('video_file_completed', path)

        self._file_manager.file_creates.subscribe(on_file_created)
        self._file_manager.file_closes.subscribe(on_file_closed)

    @property
    def stream_url(self) -> str:
        return self._stream_url

    @property
    def stream_host(self) -> str:
        return self._stream_host

    @property
    def dl_total(self) -> int:
        return self._dl_calculator.count

    @property
    def dl_rate(self) -> float:
        return self._dl_calculator.rate

    @property
    def rec_elapsed(self) -> float:
        return self._rec_calculator.elapsed

    @property
    def rec_total(self) -> int:
        return self._rec_calculator.count

    @property
    def rec_rate(self) -> float:
        return self._rec_calculator.rate

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
    def stream_format(self) -> StreamFormat:
        return self._stream_format

    @stream_format.setter
    def stream_format(self, value: StreamFormat) -> None:
        self._stream_format = value
        self._real_stream_format = None

    @property
    def quality_number(self) -> QualityNumber:
        return self._quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._quality_number = value
        self._real_quality_number = None

    @property
    def real_stream_format(self) -> StreamFormat:
        return self._real_stream_format or self.stream_format

    @property
    def real_quality_number(self) -> QualityNumber:
        return self._real_quality_number or self.quality_number

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

    @property
    def recording_path(self) -> Optional[str]:
        return self._file_manager.curr_path

    @property
    def metadata(self) -> Optional[MetaData]:
        if self._stream_processor is not None:
            return self._stream_processor.metadata
        else:
            return None

    @property
    def stream_profile(self) -> StreamProfile:
        return self._stream_profile

    def has_file(self) -> bool:
        return self._file_manager.has_file()

    def get_files(self) -> Iterator[str]:
        yield from self._file_manager.get_files()

    def clear_files(self) -> None:
        self._file_manager.clear_files()

    def can_cut_stream(self) -> bool:
        if self._stream_processor is None:
            return False
        return self._stream_processor.can_cut_stream()

    def cut_stream(self) -> bool:
        if self._stream_processor is None:
            return False
        return self._stream_processor.cut_stream()

    def update_progress_bar_info(self) -> None:
        if self._progress_bar is not None:
            self._progress_bar.set_postfix_str(self._make_pbar_postfix())

    async def _do_start(self) -> None:
        logger.debug('Starting stream recorder...')
        self._dl_calculator.reset()
        self._rec_calculator.reset()
        self._stream_url = ''
        self._stream_host = ''
        self._stream_profile = {}
        self._api_platform = 'android'
        self._use_alternative_stream = False
        self._connection_recovered.clear()
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

    @abstractmethod
    def _run(self) -> None:
        raise NotImplementedError()

    def _rotate_api_platform(self) -> None:
        if self._api_platform == 'android':
            self._api_platform = 'web'
        else:
            self._api_platform = 'android'

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
        fmt = self._real_stream_format or self.stream_format
        logger.info(
            f'Getting the live stream url... qn: {qn}, format: {fmt}, '
            f'api platform: {self._api_platform}, '
            f'use alternative stream: {self._use_alternative_stream}'
        )
        try:
            urls = self._run_coroutine(
                self._live.get_live_stream_urls(
                    qn,
                    api_platform=self._api_platform,
                    stream_format=fmt,
                )
            )
        except NoStreamQualityAvailable:
            logger.info(
                f'The specified stream quality ({qn}) is not available, '
                'will using the original stream quality (10000) instead.'
            )
            self._real_quality_number = 10000
            raise TryAgain
        except NoStreamFormatAvailable:
            if fmt == 'fmp4':
                logger.info(
                    'The specified stream format (fmp4) is not available, '
                    'falling back to stream format (ts).'
                )
                self._real_stream_format = 'ts'
            elif fmt == 'ts':
                logger.info(
                    'The specified stream format (ts) is not available, '
                    'falling back to stream format (flv).'
                )
                self._real_stream_format = 'flv'
            else:
                raise NotImplementedError(fmt)
            raise TryAgain
        except NoStreamCodecAvailable as e:
            logger.warning(repr(e))
            raise TryAgain
        except Exception as e:
            logger.warning(f'Failed to get live stream urls: {repr(e)}')
            self._rotate_api_platform()
            raise TryAgain
        else:
            logger.info(
                f'Adopted the stream format ({fmt}) and quality ({qn})'
            )
            self._real_quality_number = qn
            self._real_stream_format = fmt

        if not self._use_alternative_stream:
            url = urls[0]
        else:
            try:
                url = urls[1]
            except IndexError:
                self._use_alternative_stream = False
                self._rotate_api_platform()
                logger.info(
                    'No alternative stream url available, will using the primary'
                    f' stream url from {self._api_platform} api instead.'
                )
                raise TryAgain
        logger.info(f"Got live stream url: '{url}'")

        return url

    def _defer_retry(self, seconds: float, name: str = '') -> None:
        if seconds <= 0:
            return
        logger.debug(f'Retry {name} after {seconds} seconds')
        time.sleep(seconds)

    def _wait_for_connection_error(self) -> None:
        Thread(
            target=self._conectivity_checker,
            name=f'ConectivityChecker::{self._live.room_id}',
            daemon=True,
        ).start()
        self._connection_recovered.wait()
        self._connection_recovered.clear()

    def _conectivity_checker(self, check_interval: int = 3) -> None:
        timeout = self.disconnection_timeout
        logger.info(f'Waiting {timeout} seconds for connection recovery... ')
        timebase = time.monotonic()
        while not self._run_coroutine(self._live.check_connectivity()):
            if timeout is not None and time.monotonic() - timebase > timeout:
                logger.error(f'Connection not recovered in {timeout} seconds')
                self._stopped = True
                self._connection_recovered.set()
            time.sleep(check_interval)
        else:
            logger.info('Connection recovered')
            self._connection_recovered.set()

    def _make_pbar_postfix(self) -> str:
        return '{room_id} - {user_name}: {room_title}'.format(
            room_id=self._live.room_info.room_id,
            user_name=self._live.user_info.name,
            room_title=self._live.room_info.title,
        )

    def _make_metadata(self) -> Dict[str, Any]:
        live_start_time = datetime.fromtimestamp(
            self._live.room_info.live_start_time, timezone(timedelta(hours=8))
        )

        assert self._real_quality_number is not None
        stream_quality = '{} ({}{})'.format(
            get_quality_name(self._real_quality_number),
            self._real_quality_number,
            ', bluray' if '_bluray' in self._stream_url else '',
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
流主机: {self._stream_host}
流格式：{self._real_stream_format}
流画质：{stream_quality}
录制程序：{__prog__} v{__version__} {__github__}''',
            'description': OrderedDict({
                'UserId': str(self._live.user_info.uid),
                'UserName': self._live.user_info.name,
                'RoomId': str(self._live.room_info.room_id),
                'RoomTitle': self._live.room_info.title,
                'Area': self._live.room_info.area_name,
                'ParentArea': self._live.room_info.parent_area_name,
                'LiveStartTime': str(live_start_time),
                'StreamHost': self._stream_host,
                'StreamFormat': self._real_stream_format,
                'StreamQuality': stream_quality,
                'Recorder': f'{__prog__} v{__version__} {__github__}',
            })
        }

    def _emit_event(self, name: str, *args: Any, **kwds: Any) -> None:
        self._run_coroutine(self._emit(name, *args, **kwds))

    @aio_task_with_room_id
    async def _emit(self, *args: Any, **kwds: Any) -> None:  # type: ignore
        await super()._emit(*args, **kwds)


class StreamProxy(io.RawIOBase):
    def __init__(
        self,
        stream: io.BufferedIOBase,
        *,
        read_timeout: Optional[float] = None,
    ) -> None:
        self._stream = stream
        self._read_timmeout = read_timeout
        self._offset = 0
        self._size_updates = Subject()

    @property
    def size_updates(self) -> Observable:
        return self._size_updates

    @property
    def closed(self) -> bool:
        # always return False to avoid that `ValueError: read of closed file`,
        # raised from `CHECK_CLOSED(self, "read of closed file")`,
        # result in losing data those remaining in the buffer.
        # ref: `https://gihub.com/python/cpython/blob/63298930fb531ba2bb4f23bc3b915dbf1e17e9e1/Modules/_io/bufferedio.c#L882`  # noqa
        return False

    def fileno(self) -> int:
        return self._stream.fileno()

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if self._stream.closed:
            raise EOFError
        if self._read_timmeout:
            data = wait_for(
                self._stream.read, args=(size, ), timeout=self._read_timmeout
            )
        else:
            data = self._stream.read(size)
        self._offset += len(data)
        self._size_updates.on_next(len(data))
        return data

    def tell(self) -> int:
        return self._offset

    def readinto(self, b: Any) -> int:
        if self._stream.closed:
            raise EOFError
        if self._read_timmeout:
            n = wait_for(
                self._stream.readinto, args=(b, ), timeout=self._read_timmeout
            )
        else:
            n = self._stream.readinto(b)
        self._offset += n
        self._size_updates.on_next(n)
        return n

    def close(self) -> None:
        self._stream.close()


class OutputFileManager(BaseOutputFileManager, AsyncCooperationMixin):
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
            uname=escape_path(self._live.user_info.name),
            title=escape_path(self._live.room_info.title),
            area=escape_path(self._live.room_info.area_name),
            parent_area=escape_path(self._live.room_info.parent_area_name),
            year=date_time.year,
            month=str(date_time.month).rjust(2, '0'),
            day=str(date_time.day).rjust(2, '0'),
            hour=str(date_time.hour).rjust(2, '0'),
            minute=str(date_time.minute).rjust(2, '0'),
            second=str(date_time.second).rjust(2, '0'),
        )

        pathname = os.path.abspath(
            os.path.expanduser(os.path.join(self.out_dir, relpath) + '.flv')
        )
        os.makedirs(os.path.dirname(pathname), exist_ok=True)
        while os.path.exists(pathname):
            root, ext = os.path.splitext(pathname)
            m = re.search(r'_\((\d+)\)$', root)
            if m is None:
                root += '_(1)'
            else:
                root = re.sub(r'\(\d+\)$', f'({int(m.group(1)) + 1})', root)
            pathname = root + ext

        return pathname
