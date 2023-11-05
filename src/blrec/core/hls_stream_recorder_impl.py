from typing import Optional

from loguru import logger
from reactivex.scheduler import NewThreadScheduler

from blrec.bili.live import Live
from blrec.bili.live_monitor import LiveMonitor
from blrec.bili.typing import QualityNumber
from blrec.hls import operators as hls_ops
from blrec.hls.metadata_dumper import MetadataDumper
from blrec.utils import operators as utils_ops

from . import operators as core_ops
from .stream_recorder_impl import StreamRecorderImpl

__all__ = ('HLSStreamRecorderImpl',)


class HLSStreamRecorderImpl(StreamRecorderImpl):
    def __init__(
        self,
        live: Live,
        live_monitor: LiveMonitor,
        out_dir: str,
        path_template: str,
        *,
        quality_number: QualityNumber = 10000,
        buffer_size: Optional[int] = None,
        read_timeout: Optional[int] = None,
        disconnection_timeout: Optional[int] = None,
        filesize_limit: int = 0,
        duration_limit: int = 0,
    ) -> None:
        super().__init__(
            live=live,
            live_monitor=live_monitor,
            out_dir=out_dir,
            path_template=path_template,
            stream_format='fmp4',
            recording_mode='standard',
            quality_number=quality_number,
            buffer_size=buffer_size,
            read_timeout=read_timeout,
            disconnection_timeout=disconnection_timeout,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )

        self._playlist_fetcher = hls_ops.PlaylistFetcher(self._live, self._session)
        self._playlist_resolver = hls_ops.PlaylistResolver(self._stream_url_resolver)
        self._segment_fetcher = hls_ops.SegmentFetcher(
            self._live, self._session, self._stream_url_resolver
        )
        self._segment_dumper = hls_ops.SegmentDumper(self._path_provider)
        self._playlist_dumper = hls_ops.PlaylistDumper(self._segment_dumper)
        self._ff_metadata_dumper = MetadataDumper(
            self._segment_dumper, self._metadata_provider
        )

        self._cutter = hls_ops.Cutter(self._playlist_dumper)
        self._limiter = hls_ops.Limiter(
            self._playlist_dumper,
            self._segment_dumper,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )
        self._prober = hls_ops.Prober()
        self._analyser = hls_ops.Analyser(
            self._playlist_dumper, self._segment_dumper, self._prober
        )
        self._dl_statistics = core_ops.SizedStatistics()

        self._recording_monitor = core_ops.RecordingMonitor(
            live,
            lambda: self._playlist_dumper.duration,
            self._playlist_dumper.duration_updated,
        )

        self._prober.profiles.subscribe(self._on_profile_updated)
        self._segment_dumper.file_opened.subscribe(self._on_video_file_opened)
        self._segment_dumper.file_closed.subscribe(self._on_video_file_closed)
        self._playlist_dumper.segments_lost.subscribe(self._on_duration_lost)
        self._recording_monitor.interrupted.subscribe(self._on_recording_interrupted)
        self._recording_monitor.recovered.subscribe(self._on_recording_recovered)

    @property
    def recording_path(self) -> Optional[str]:
        return self._segment_dumper.path

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
    def metadata(self) -> Optional[hls_ops.MetaData]:
        return self._analyser.make_metadata()

    def can_cut_stream(self) -> bool:
        return self._cutter.can_cut_stream()

    def cut_stream(self) -> bool:
        return self._cutter.cut_stream()

    def _on_start(self) -> None:
        self._ff_metadata_dumper.enable()

    def _on_stop(self) -> None:
        self._ff_metadata_dumper.disable()

    def _run(self) -> None:
        with logger.contextualize(room_id=self._live.room_id):
            self._subscription = (
                self._stream_param_holder.get_stream_params()  # type: ignore
                .pipe(
                    self._stream_url_resolver,
                    self._playlist_fetcher,
                    self._recording_monitor,
                    self._connection_error_handler,
                    self._request_exception_handler,
                    self._playlist_resolver,
                    utils_ops.observe_on_new_thread(
                        queue_size=60,
                        thread_name=f'SegmentFetcher::{self._live.room_id}',
                        logger_context={'room_id': self._live.room_id},
                    ),
                    self._segment_fetcher,
                    self._dl_statistics,
                    self._prober,
                    self._analyser,
                    self._cutter,
                    self._limiter,
                    self._segment_dumper,
                    self._rec_statistics,
                    self._progress_bar,
                    self._playlist_dumper,
                    self._exception_handler,
                )
                .subscribe(
                    on_completed=self._on_completed,
                    scheduler=NewThreadScheduler(
                        self._thread_factory('HLSStreamRecorder')
                    ),
                )
            )
