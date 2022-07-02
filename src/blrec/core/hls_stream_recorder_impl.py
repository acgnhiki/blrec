import logging
from typing import Optional

from reactivex import operators as ops
from reactivex.scheduler import NewThreadScheduler

from ..bili.live import Live
from ..bili.typing import QualityNumber
from ..flv import operators as flv_ops
from . import operators as core_ops
from .stream_recorder_impl import StreamRecorderImpl

__all__ = ('HLSStreamRecorderImpl',)


logger = logging.getLogger(__name__)


class HLSStreamRecorderImpl(StreamRecorderImpl):
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
            quality_number=quality_number,
            buffer_size=buffer_size,
            read_timeout=read_timeout,
            disconnection_timeout=disconnection_timeout,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )

        self._playlist_fetcher = core_ops.PlaylistFetcher(self._live, self._session)
        self._playlist_resolver = core_ops.PlaylistResolver()
        self._segment_fetcher = core_ops.SegmentFetcher(self._live, self._session)
        self._segment_remuxer = core_ops.SegmentRemuxer(live)

    def _run(self) -> None:
        self._subscription = (
            self._stream_param_holder.get_stream_params()  # type: ignore
            .pipe(
                self._stream_url_resolver,
                ops.subscribe_on(
                    NewThreadScheduler(self._thread_factory('PlaylistFetcher'))
                ),
                self._playlist_fetcher,
                self._recording_monitor,
                self._connection_error_handler,
                self._request_exception_handler,
                self._playlist_resolver,
                ops.observe_on(
                    NewThreadScheduler(self._thread_factory('SegmentFetcher'))
                ),
                self._segment_fetcher,
                self._dl_statistics,
                self._prober,
                ops.observe_on(
                    NewThreadScheduler(self._thread_factory('SegmentRemuxer'))
                ),
                self._segment_remuxer,
                ops.observe_on(
                    NewThreadScheduler(self._thread_factory('StreamRecorder'))
                ),
                self._stream_parser,
                flv_ops.process(),
                self._cutter,
                self._limiter,
                self._join_point_extractor,
                self._injector,
                self._analyser,
                self._dumper,
                self._rec_statistics,
                self._progress_bar,
                self._exception_handler,
            )
            .subscribe(on_completed=self._on_completed)
        )
