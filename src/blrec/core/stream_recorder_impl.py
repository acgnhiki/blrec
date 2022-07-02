import logging
from abc import ABC, abstractmethod
from datetime import datetime
from threading import Thread
from typing import Any, Iterator, List, Optional, Tuple, Union

import requests
import urllib3
from reactivex import abc
from reactivex.typing import StartableFactory, StartableTarget

from ..bili.live import Live
from ..bili.typing import QualityNumber, StreamFormat
from ..event.event_emitter import EventEmitter, EventListener
from ..flv import operators as flv_ops
from ..flv.metadata_dumper import MetadataDumper
from ..flv.operators import StreamProfile
from ..flv.utils import format_timestamp
from ..logging.room_id import aio_task_with_room_id
from ..utils.mixins import AsyncCooperationMixin, AsyncStoppableMixin
from . import operators as core_ops
from .metadata_provider import MetadataProvider
from .path_provider import PathProvider
from .stream_param_holder import StreamParamHolder

__all__ = ('StreamRecorderImpl',)


logger = logging.getLogger(__name__)
logging.getLogger(urllib3.__name__).setLevel(logging.WARNING)


class StreamRecorderEventListener(EventListener):
    async def on_video_file_created(self, path: str, record_start_time: int) -> None:
        ...

    async def on_video_file_completed(self, path: str) -> None:
        ...

    async def on_stream_recording_interrupted(self, duratin: float) -> None:
        ...

    async def on_stream_recording_recovered(self, timestamp: int) -> None:
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
        self._session = requests.Session()
        self._stream_param_holder = StreamParamHolder(
            stream_format=stream_format, quality_number=quality_number
        )
        self._stream_url_resolver = core_ops.StreamURLResolver(
            live, self._stream_param_holder
        )
        self._stream_fetcher = core_ops.StreamFetcher(
            live, self._session, read_timeout=read_timeout
        )
        self._stream_parser = core_ops.StreamParser(
            self._stream_param_holder,
            ignore_eof=stream_format != 'flv',
            ignore_value_error=stream_format != 'flv',
        )
        self._progress_bar = core_ops.ProgressBar(live)
        self._analyser = flv_ops.Analyser()
        self._metadata_provider = MetadataProvider(live, self)
        self._injector = flv_ops.Injector(self._metadata_provider)
        self._join_point_extractor = flv_ops.JoinPointExtractor()
        self._limiter = flv_ops.Limiter(filesize_limit, duration_limit)
        self._cutter = flv_ops.Cutter()
        self._path_provider = PathProvider(live, out_dir, path_template)
        self._dumper = flv_ops.Dumper(self._path_provider, buffer_size)
        self._rec_statistics = core_ops.SizedStatistics()
        self._recording_monitor = core_ops.RecordingMonitor(live, self._analyser)

        self._prober: Union[flv_ops.Prober, core_ops.HLSProber]
        self._dl_statistics: Union[core_ops.StreamStatistics, core_ops.SizedStatistics]
        if stream_format == 'flv':
            self._prober = flv_ops.Prober()
            self._dl_statistics = core_ops.StreamStatistics()
        else:
            self._prober = core_ops.HLSProber()
            self._dl_statistics = core_ops.SizedStatistics()

        self._request_exception_handler = core_ops.RequestExceptionHandler()
        self._connection_error_handler = core_ops.ConnectionErrorHandler(
            live, disconnection_timeout=disconnection_timeout
        )
        self._exception_handler = core_ops.ExceptionHandler()
        self._metadata_dumper = MetadataDumper(
            self._dumper, self._analyser, self._join_point_extractor
        )
        self._metadata_dumper.enable()

        self._subscription: abc.DisposableBase
        self._completed: bool = False

        self._threads: List[Thread] = []
        self._files: List[str] = []
        self._stream_profile: StreamProfile = {}
        self._record_start_time: Optional[int] = None
        self._stream_available_time: Optional[int] = None
        self._hls_stream_available_time: Optional[int] = None

        def on_profile_updated(profile: StreamProfile) -> None:
            self._stream_profile = profile

        self._prober.profiles.subscribe(on_profile_updated)

        def on_file_opened(args: Tuple[str, int]) -> None:
            logger.info(f"Video file created: '{args[0]}'")
            self._files.append(args[0])
            self._record_start_time = args[1]
            self._emit_event('video_file_created', *args)

        def on_file_closed(path: str) -> None:
            logger.info(f"Video file completed: '{path}'")
            self._emit_event('video_file_completed', path)

        self._dumper.file_opened.subscribe(on_file_opened)
        self._dumper.file_closed.subscribe(on_file_closed)

        def on_recording_interrupted(duration: float) -> None:
            duration_string = format_timestamp(int(duration * 1000))
            logger.info(f'Recording interrupted, current duration: {duration_string}')
            self._emit_event('stream_recording_interrupted', duration)

        def on_recording_recovered(timestamp: int) -> None:
            datetime_string = datetime.fromtimestamp(timestamp).isoformat()
            logger.info(f'Recording recovered, current date time {(datetime_string)}')
            self._emit_event('stream_recording_recovered', timestamp)

        self._recording_monitor.interrupted.subscribe(on_recording_interrupted)
        self._recording_monitor.recovered.subscribe(on_recording_recovered)

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
        return self._limiter.filesize_limit

    @filesize_limit.setter
    def filesize_limit(self, value: int) -> None:
        self._limiter.filesize_limit = value

    @property
    def duration_limit(self) -> int:
        return self._limiter.duration_limit

    @duration_limit.setter
    def duration_limit(self, value: int) -> None:
        self._limiter.duration_limit = value

    @property
    def read_timeout(self) -> int:
        return self._stream_fetcher.read_timeout

    @read_timeout.setter
    def read_timeout(self, value: int) -> None:
        self._stream_fetcher.read_timeout = value

    @property
    def disconnection_timeout(self) -> int:
        return self._connection_error_handler.disconnection_timeout

    @disconnection_timeout.setter
    def disconnection_timeout(self, value: int) -> None:
        self._connection_error_handler.disconnection_timeout = value

    @property
    def buffer_size(self) -> int:
        return self._dumper.buffer_size

    @buffer_size.setter
    def buffer_size(self, value: int) -> None:
        self._dumper.buffer_size = value

    @property
    def recording_path(self) -> Optional[str]:
        return self._dumper.path

    @property
    def metadata(self) -> Optional[flv_ops.MetaData]:
        try:
            return self._analyser.make_metadata()
        except Exception:
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
        return self._cutter.can_cut_stream()

    def cut_stream(self) -> bool:
        return self._cutter.cut_stream()

    def update_progress_bar_info(self) -> None:
        self._progress_bar.update_bar_info()

    def _reset(self) -> None:
        self._files.clear()
        self._stream_profile = {}
        self._record_start_time = None
        self._completed = False

    async def _do_start(self) -> None:
        logger.debug('Starting stream recorder...')
        self._reset()
        self._run()
        logger.debug('Started stream recorder')

    async def _do_stop(self) -> None:
        logger.debug('Stopping stream recorder...')
        self._stream_param_holder.cancel()
        thread = self._thread_factory('StreamRecorderDisposer')(self._dispose)
        thread.start()
        for thread in self._threads:
            await self._loop.run_in_executor(None, thread.join, 30)
        self._threads.clear()
        logger.debug('Stopped stream recorder')

    @abstractmethod
    def _run(self) -> None:
        raise NotImplementedError()

    def _thread_factory(self, name: str) -> StartableFactory:
        def factory(target: StartableTarget) -> Thread:
            thread = Thread(
                target=target, daemon=True, name=f'{name}::{self._live.room_id}'
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

    def _emit_event(self, name: str, *args: Any, **kwds: Any) -> None:
        self._run_coroutine(self._emit(name, *args, **kwds))

    @aio_task_with_room_id
    async def _emit(self, *args: Any, **kwds: Any) -> None:  # type: ignore
        await super()._emit(*args, **kwds)
