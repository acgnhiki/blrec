import logging
from typing import Optional

from reactivex import operators as ops
from reactivex.scheduler import NewThreadScheduler

from blrec.bili.live import Live
from blrec.bili.typing import QualityNumber
from blrec.hls import operators as hls_ops
from blrec.hls.metadata_dumper import MetadataDumper

from . import operators as core_ops
from .stream_recorder_impl import StreamRecorderImpl

__all__ = ('HLSRawStreamRecorderImpl',)


logger = logging.getLogger(__name__)


class HLSRawStreamRecorderImpl(StreamRecorderImpl):
    def __init__(
        self,
        live: Live,
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
            out_dir=out_dir,
            path_template=path_template,
            stream_format='fmp4',
            recording_mode='raw',
            quality_number=quality_number,
            buffer_size=buffer_size,
            read_timeout=read_timeout,
            disconnection_timeout=disconnection_timeout,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )

        self._playlist_fetcher = hls_ops.PlaylistFetcher(self._live, self._session)
        self._playlist_dumper = hls_ops.PlaylistDumper(self._path_provider)
        self._segment_fetcher = hls_ops.SegmentFetcher(self._live, self._session)
        self._segment_dumper = hls_ops.SegmentDumper(self._playlist_dumper)
        self._ff_metadata_dumper = MetadataDumper(
            self._playlist_dumper, self._metadata_provider
        )

        self._prober = hls_ops.Prober()
        self._dl_statistics = core_ops.SizedStatistics()

        self._recording_monitor = core_ops.RecordingMonitor(
            live, lambda: self._playlist_dumper.duration
        )

        self._prober.profiles.subscribe(self._on_profile_updated)
        self._playlist_dumper.file_opened.subscribe(self._on_video_file_opened)
        self._playlist_dumper.file_closed.subscribe(self._on_video_file_closed)
        self._recording_monitor.interrupted.subscribe(self._on_recording_interrupted)
        self._recording_monitor.recovered.subscribe(self._on_recording_recovered)

    @property
    def recording_path(self) -> Optional[str]:
        return self._playlist_dumper.path

    def _on_start(self) -> None:
        self._ff_metadata_dumper.enable()

    def _on_stop(self) -> None:
        self._ff_metadata_dumper.disable()

    def _run(self) -> None:
        self._subscription = (
            self._stream_param_holder.get_stream_params()  # type: ignore
            .pipe(
                self._stream_url_resolver,
                ops.subscribe_on(
                    NewThreadScheduler(self._thread_factory('PlaylistDownloader'))
                ),
                self._playlist_fetcher,
                self._recording_monitor,
                self._connection_error_handler,
                self._request_exception_handler,
                self._playlist_dumper,
                ops.observe_on(
                    NewThreadScheduler(self._thread_factory('SegmentDownloader'))
                ),
                self._segment_fetcher,
                self._dl_statistics,
                self._prober,
                self._segment_dumper,
                self._rec_statistics,
                self._progress_bar,
                self._exception_handler,
            )
            .subscribe(on_completed=self._on_completed)
        )
