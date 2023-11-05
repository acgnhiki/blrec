import asyncio
import time
from typing import Iterator, Optional

from loguru import logger

from blrec.bili.live import Live
from blrec.bili.live_monitor import LiveMonitor
from blrec.bili.typing import QualityNumber, StreamFormat
from blrec.event.event_emitter import EventEmitter
from blrec.flv.operators import StreamProfile
from blrec.setting.typing import RecordingMode
from blrec.utils.libc import malloc_trim
from blrec.utils.mixins import AsyncStoppableMixin

from .flv_stream_recorder_impl import FLVStreamRecorderImpl
from .hls_stream_recorder_impl import HLSStreamRecorderImpl
from .stream_recorder_impl import StreamRecorderEventListener
from .typing import MetaData

__all__ = 'StreamRecorder', 'StreamRecorderEventListener'


class StreamRecorder(
    StreamRecorderEventListener,
    EventEmitter[StreamRecorderEventListener],
    AsyncStoppableMixin,
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
        fmp4_stream_timeout: int = 10,
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
        self.stream_format = stream_format
        self.recording_mode = recording_mode
        self.fmp4_stream_timeout = fmp4_stream_timeout

        if stream_format == 'flv':
            cls = FLVStreamRecorderImpl
        elif stream_format == 'fmp4':
            cls = HLSStreamRecorderImpl  # type: ignore
        else:
            self._logger.warning(
                f'The specified stream format ({stream_format}) is '
                'unsupported, will using the stream format (flv) instead.'
            )
            self.stream_format = 'flv'
            cls = FLVStreamRecorderImpl

        self._impl = cls(
            live=live,
            live_monitor=live_monitor,
            out_dir=out_dir,
            path_template=path_template,
            quality_number=quality_number,
            buffer_size=buffer_size,
            read_timeout=read_timeout,
            disconnection_timeout=disconnection_timeout,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )

        self._impl.add_listener(self)

    @property
    def stream_url(self) -> str:
        return self._impl.stream_url

    @property
    def stream_host(self) -> str:
        return self._impl.stream_host

    @property
    def record_start_time(self) -> Optional[int]:
        return self._impl.record_start_time

    @property
    def stream_available_time(self) -> Optional[int]:
        return self._impl.stream_available_time

    @stream_available_time.setter
    def stream_available_time(self, ts: Optional[int]) -> None:
        self._impl.stream_available_time = ts

    @property
    def hls_stream_available_time(self) -> Optional[int]:
        return self._impl.hls_stream_available_time

    @hls_stream_available_time.setter
    def hls_stream_available_time(self, ts: Optional[int]) -> None:
        self._impl.hls_stream_available_time = ts

    @property
    def dl_total(self) -> int:
        return self._impl.dl_total

    @property
    def dl_rate(self) -> float:
        return self._impl.dl_rate

    @property
    def rec_elapsed(self) -> float:
        return self._impl.rec_elapsed

    @property
    def rec_total(self) -> int:
        return self._impl.rec_total

    @property
    def rec_rate(self) -> float:
        return self._impl.rec_rate

    @property
    def out_dir(self) -> str:
        return self._impl.out_dir

    @out_dir.setter
    def out_dir(self, value: str) -> None:
        self._impl.out_dir = value

    @property
    def path_template(self) -> str:
        return self._impl.path_template

    @path_template.setter
    def path_template(self, value: str) -> None:
        self._impl.path_template = value

    @property
    def quality_number(self) -> QualityNumber:
        return self._impl.quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._impl.quality_number = value

    @property
    def real_stream_format(self) -> Optional[StreamFormat]:
        if self.stopped:
            return None
        return self._impl.stream_format

    @property
    def real_quality_number(self) -> Optional[QualityNumber]:
        return self._impl.real_quality_number

    @property
    def buffer_size(self) -> int:
        return self._impl.buffer_size

    @buffer_size.setter
    def buffer_size(self, value: int) -> None:
        self._impl.buffer_size = value

    @property
    def read_timeout(self) -> int:
        return self._impl.read_timeout

    @read_timeout.setter
    def read_timeout(self, value: int) -> None:
        self._impl.read_timeout = value

    @property
    def disconnection_timeout(self) -> int:
        return self._impl.disconnection_timeout

    @disconnection_timeout.setter
    def disconnection_timeout(self, value: int) -> None:
        self._impl.disconnection_timeout = value

    @property
    def filesize_limit(self) -> int:
        return self._impl.filesize_limit

    @filesize_limit.setter
    def filesize_limit(self, value: int) -> None:
        self._impl.filesize_limit = value

    @property
    def duration_limit(self) -> int:
        return self._impl.duration_limit

    @duration_limit.setter
    def duration_limit(self, value: int) -> None:
        self._impl.duration_limit = value

    @property
    def recording_path(self) -> Optional[str]:
        return self._impl.recording_path

    @property
    def metadata(self) -> Optional[MetaData]:
        return self._impl.metadata

    @property
    def stream_profile(self) -> StreamProfile:
        return self._impl.stream_profile

    def has_file(self) -> bool:
        return self._impl.has_file()

    def get_files(self) -> Iterator[str]:
        yield from self._impl.get_files()

    def clear_files(self) -> None:
        self._impl.clear_files()

    def can_cut_stream(self) -> bool:
        return self._impl.can_cut_stream()

    def cut_stream(self) -> bool:
        return self._impl.cut_stream()

    def update_progress_bar_info(self) -> None:
        self._impl.update_progress_bar_info()

    @property
    def stopped(self) -> bool:
        return self._impl.stopped

    async def _do_start(self) -> None:
        self.hls_stream_available_time = None
        stream_format = self.stream_format

        if self._live.has_no_flv_streams():
            if stream_format == 'flv':
                self._logger.warning(
                    'The specified stream format (flv) is not available, '
                    'falling back to stream format (fmp4).'
                )
                stream_format = 'fmp4'
            self.hls_stream_available_time = self.stream_available_time
        else:
            if stream_format == 'fmp4':
                self._logger.info('Waiting for the fmp4 stream becomes available...')
                available = await self._wait_fmp4_stream()
                if available:
                    if self.stream_available_time is not None:
                        self.hls_stream_available_time = (
                            await self._live.get_timestamp()
                        )
                else:
                    self._logger.warning(
                        'The specified stream format (fmp4) is not available '
                        f'in {self.fmp4_stream_timeout} seconcds, '
                        'falling back to stream format (flv).'
                    )
                    stream_format = 'flv'

        self._change_impl(stream_format)
        await self._impl.start()

    async def _do_stop(self) -> None:
        await self._impl.stop()
        malloc_trim(0)

    async def on_video_file_created(self, path: str, record_start_time: int) -> None:
        await self._emit('video_file_created', path, record_start_time)

    async def on_video_file_completed(self, path: str) -> None:
        await self._emit('video_file_completed', path)

    async def on_stream_recording_interrupted(
        self, timestamp: float, duration: float
    ) -> None:
        await self._emit('stream_recording_interrupted', timestamp, duration)

    async def on_stream_recording_recovered(self, timestamp: float) -> None:
        await self._emit('stream_recording_recovered', timestamp)

    async def on_stream_recording_completed(self) -> None:
        await self._emit('stream_recording_completed')

    async def _wait_fmp4_stream(self) -> bool:
        end_time = time.monotonic() + self.fmp4_stream_timeout
        available = False  # debounce
        while True:
            try:
                await self._impl._live.get_live_stream_url(stream_format='fmp4')
            except Exception:
                available = False
                if time.monotonic() > end_time:
                    return False
            else:
                if available:
                    return True
                else:
                    available = True
            await asyncio.sleep(1)

    def _change_impl(self, stream_format: StreamFormat) -> None:
        if stream_format == 'flv':
            cls = FLVStreamRecorderImpl
        elif stream_format == 'fmp4':
            cls = HLSStreamRecorderImpl  # type: ignore
        else:
            self._logger.warning(
                f'The specified stream format ({stream_format}) is '
                'unsupported, will using the stream format (flv) instead.'
            )
            cls = FLVStreamRecorderImpl

        if self._impl.__class__ == cls:
            return

        self._impl.remove_listener(self)
        stream_available_time = self._impl.stream_available_time
        hls_stream_available_time = self._impl.hls_stream_available_time

        self._impl = cls(
            live=self._impl._live,
            live_monitor=self._impl._live_monitor,
            out_dir=self._impl.out_dir,
            path_template=self._impl.path_template,
            quality_number=self._impl.quality_number,
            buffer_size=self._impl.buffer_size,
            read_timeout=self._impl.read_timeout,
            disconnection_timeout=self._impl.disconnection_timeout,
            filesize_limit=self._impl.filesize_limit,
            duration_limit=self._impl.duration_limit,
        )

        self._impl.add_listener(self)
        self._impl.stream_available_time = stream_available_time
        self._impl.hls_stream_available_time = hls_stream_available_time

        self._logger.debug(f'Changed stream recorder impl to {cls.__name__}')
