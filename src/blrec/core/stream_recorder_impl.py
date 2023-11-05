import io
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from threading import Thread
from typing import Any, Iterator, List, Optional, Tuple, Union

import requests
import urllib3
from loguru import logger
from reactivex import abc
from reactivex.typing import StartableFactory, StartableTarget

from blrec.bili.live import Live
from blrec.bili.live_monitor import LiveMonitor
from blrec.bili.typing import QualityNumber, StreamFormat
from blrec.event.event_emitter import EventEmitter, EventListener
from blrec.flv import operators as flv_ops
from blrec.flv.operators import StreamProfile
from blrec.flv.utils import format_timestamp
from blrec.hls import operators as hls_ops
from blrec.setting.typing import RecordingMode
from blrec.utils.mixins import AsyncCooperationMixin, AsyncStoppableMixin

from . import operators as core_ops
from .metadata_provider import MetadataProvider
from .path_provider import PathProvider
from .stream_param_holder import StreamParamHolder

__all__ = ('StreamRecorderImpl',)


logging.getLogger(urllib3.__name__).setLevel(logging.WARNING)


class StreamRecorderEventListener(EventListener):
    async def on_video_file_created(self, path: str, record_start_time: int) -> None:
        ...

    async def on_video_file_completed(self, path: str) -> None:
        ...

    async def on_stream_recording_interrupted(
        self, timestamp: float, duration: float
    ) -> None:
        ...

    async def on_stream_recording_recovered(self, timestamp: float) -> None:
        ...

    async def on_duration_lost(self, duration: float) -> None:
        ...

    async def on_stream_recording_completed(self) -> None:
        ...


class StreamRecorderImpl(
    EventEmitter[StreamRecorderEventListener],
    AsyncCooperationMixin,
    AsyncStoppableMixin,
    ABC,
):
    def __init__(
        self,
        live: Live,
        live_monitor: LiveMonitor,
        out_dir: str,
        path_template: str,
        *,
        stream_format: StreamFormat = 'flv',
        recording_mode: RecordingMode = 'standard',
        quality_number: QualityNumber = 10000,
        buffer_size: Optional[int] = None,
        read_timeout: Optional[int] = None,
        disconnection_timeout: Optional[int] = None,
        filesize_limit: int = 0,
        duration_limit: int = 0,
    ) -> None:
        super().__init__()
        self._logger_context = {'room_id': live.room_id}
        self._logger = logger.bind(**self._logger_context)

        self._live = live
        self._live_monitor = live_monitor
        self._session = requests.Session()

        self._recording_mode = recording_mode
        self._buffer_size = buffer_size or io.DEFAULT_BUFFER_SIZE
        self._read_timeout = read_timeout or 3
        self._filesize_limit = filesize_limit
        self._duration_limit = duration_limit

        self._stream_param_holder = StreamParamHolder(
            stream_format=stream_format, quality_number=quality_number
        )
        self._stream_url_resolver = core_ops.StreamURLResolver(
            live, self._session, live_monitor, self._stream_param_holder
        )
        self._progress_bar = core_ops.ProgressBar(live)
        self._metadata_provider = MetadataProvider(live, self)
        self._path_provider = PathProvider(live, out_dir, path_template)
        self._rec_statistics = core_ops.SizedStatistics()
        self._dl_statistics: Union[core_ops.StreamStatistics, core_ops.SizedStatistics]

        self._request_exception_handler = core_ops.RequestExceptionHandler(
            self._stream_url_resolver
        )
        self._connection_error_handler = core_ops.ConnectionErrorHandler(
            live, disconnection_timeout=disconnection_timeout
        )
        self._exception_handler = core_ops.ExceptionHandler()

        self._subscription: abc.DisposableBase
        self._completed: bool = False

        self._threads: List[Thread] = []
        self._files: List[str] = []
        self._stream_profile: StreamProfile = {}
        self._record_start_time: Optional[int] = None
        self._stream_available_time: Optional[int] = None
        self._hls_stream_available_time: Optional[int] = None

    @property
    def stream_url(self) -> str:
        return self._stream_url_resolver.stream_url

    @property
    def stream_host(self) -> str:
        return self._stream_url_resolver.stream_host

    @property
    def record_start_time(self) -> Optional[int]:
        return self._record_start_time

    @property
    def stream_available_time(self) -> Optional[int]:
        return self._stream_available_time

    @stream_available_time.setter
    def stream_available_time(self, ts: Optional[int]) -> None:
        self._stream_available_time = ts

    @property
    def hls_stream_available_time(self) -> Optional[int]:
        return self._hls_stream_available_time

    @hls_stream_available_time.setter
    def hls_stream_available_time(self, ts: Optional[int]) -> None:
        self._hls_stream_available_time = ts

    @property
    def dl_total(self) -> int:
        return self._dl_statistics.count

    @property
    def dl_rate(self) -> float:
        return self._dl_statistics.rate

    @property
    def rec_elapsed(self) -> float:
        return self._rec_statistics.elapsed

    @property
    def rec_total(self) -> int:
        return self._rec_statistics.count

    @property
    def rec_rate(self) -> float:
        return self._rec_statistics.rate

    @property
    def out_dir(self) -> str:
        return self._path_provider.out_dir

    @out_dir.setter
    def out_dir(self, value: str) -> None:
        self._path_provider.out_dir = value

    @property
    def path_template(self) -> str:
        return self._path_provider.path_template

    @path_template.setter
    def path_template(self, value: str) -> None:
        self._path_provider.path_template = value

    @property
    def stream_format(self) -> StreamFormat:
        return self._stream_param_holder.stream_format

    @property
    def recording_mode(self) -> RecordingMode:
        return self._recording_mode

    @property
    def quality_number(self) -> QualityNumber:
        return self._stream_param_holder.quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._stream_param_holder.quality_number = value

    @property
    def real_quality_number(self) -> Optional[QualityNumber]:
        if self.stopped:
            return None
        return self._stream_param_holder.real_quality_number

    @property
    def filesize_limit(self) -> int:
        return self._filesize_limit

    @filesize_limit.setter
    def filesize_limit(self, value: int) -> None:
        self._filesize_limit = value

    @property
    def duration_limit(self) -> int:
        return self._duration_limit

    @duration_limit.setter
    def duration_limit(self, value: int) -> None:
        self._duration_limit = value

    @property
    def read_timeout(self) -> int:
        return self._read_timeout

    @read_timeout.setter
    def read_timeout(self, value: int) -> None:
        self._read_timeout = value

    @property
    def disconnection_timeout(self) -> int:
        return self._connection_error_handler.disconnection_timeout

    @disconnection_timeout.setter
    def disconnection_timeout(self, value: int) -> None:
        self._connection_error_handler.disconnection_timeout = value

    @property
    def buffer_size(self) -> int:
        return self._buffer_size

    @buffer_size.setter
    def buffer_size(self, value: int) -> None:
        self._buffer_size = value

    @property
    def recording_path(self) -> Optional[str]:
        return ''

    @property
    def metadata(self) -> Optional[Union[flv_ops.MetaData, hls_ops.MetaData]]:
        return None

    @property
    def stream_profile(self) -> StreamProfile:
        return self._stream_profile

    def has_file(self) -> bool:
        return bool(self._files)

    def get_files(self) -> Iterator[str]:
        yield from iter(self._files)

    def clear_files(self) -> None:
        self._files.clear()

    def can_cut_stream(self) -> bool:
        return False

    def cut_stream(self) -> bool:
        return False

    def update_progress_bar_info(self) -> None:
        self._progress_bar.update_bar_info()

    def _reset(self) -> None:
        self._files.clear()
        self._stream_profile = {}
        self._record_start_time = None
        self._completed = False

    async def _do_start(self) -> None:
        self._logger.debug('Starting stream recorder...')
        self._on_start()
        self._reset()
        self._run()
        self._logger.debug('Started stream recorder')

    async def _do_stop(self) -> None:
        self._logger.debug('Stopping stream recorder...')
        self._stream_param_holder.cancel()
        thread = self._thread_factory('StreamRecorderDisposer')(self._dispose)
        thread.start()
        for thread in self._threads:
            await self._loop.run_in_executor(None, thread.join, 30)
        self._threads.clear()
        self._on_stop()
        self._logger.debug('Stopped stream recorder')

    def _on_start(self) -> None:
        pass

    def _on_stop(self) -> None:
        pass

    @abstractmethod
    def _run(self) -> None:
        raise NotImplementedError()

    def _thread_factory(self, name: str) -> StartableFactory:
        def factory(target: StartableTarget) -> Thread:
            def run() -> None:
                with logger.contextualize(room_id=self._live.room_id):
                    target()

            thread = Thread(
                target=run, daemon=True, name=f'{name}::{self._live.room_id}'
            )
            self._threads.append(thread)

            return thread

        return factory

    def _dispose(self) -> None:
        self._subscription.dispose()
        del self._subscription
        self._on_completed()

    def _on_completed(self) -> None:
        if self._completed:
            return
        self._completed = True

        self._dl_statistics.freeze()
        self._rec_statistics.freeze()
        self._emit_event('stream_recording_completed')

    def _on_profile_updated(self, profile: StreamProfile) -> None:
        self._logger.debug(f'Stream profile: {profile}')
        self._stream_profile = profile

    def _on_video_file_opened(self, args: Tuple[str, int]) -> None:
        self._logger.info(f"Video file created: '{args[0]}'")
        self._files.append(args[0])
        self._record_start_time = args[1]
        self._emit_event('video_file_created', *args)

    def _on_video_file_closed(self, path: str) -> None:
        self._logger.info(f"Video file completed: '{path}'")
        self._emit_event('video_file_completed', path)

    def _on_recording_interrupted(self, args: Tuple[float, float]) -> None:
        timestamp, duration = args[0], args[1]
        datetime_string = datetime.fromtimestamp(timestamp).isoformat()
        duration_string = format_timestamp(int(duration * 1000))
        self._logger.warning(
            f'Recording interrupted, datetime: {datetime_string}, '
            f'duration: {duration_string}'
        )
        self._emit_event('stream_recording_interrupted', timestamp, duration)

    def _on_recording_recovered(self, timestamp: float) -> None:
        datetime_string = datetime.fromtimestamp(timestamp).isoformat()
        self._logger.warning(f'Recording recovered, datetime: {(datetime_string)}')
        self._emit_event('stream_recording_recovered', timestamp)

    def _on_duration_lost(self, duration: float) -> None:
        self._logger.warning(f'Total duration lost: ≈ {(duration)} s')
        self._emit_event('duration_lost', duration)

    def _emit_event(self, name: str, *args: Any, **kwds: Any) -> None:
        self._call_coroutine(self._emit(name, *args, **kwds))
