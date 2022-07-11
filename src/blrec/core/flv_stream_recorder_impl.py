import logging
from typing import Optional

from reactivex.scheduler import NewThreadScheduler

from ..bili.live import Live
from ..bili.typing import QualityNumber
from ..flv import operators as flv_ops
from ..utils.mixins import SupportDebugMixin
from .stream_recorder_impl import StreamRecorderImpl

__all__ = ('FLVStreamRecorderImpl',)


logger = logging.getLogger(__name__)


class FLVStreamRecorderImpl(StreamRecorderImpl, SupportDebugMixin):
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
            stream_format='flv',
            quality_number=quality_number,
            buffer_size=buffer_size,
            read_timeout=read_timeout,
            disconnection_timeout=disconnection_timeout,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )
        self._init_for_debug(live.room_id)

    def _run(self) -> None:
        self._subscription = (
            self._stream_param_holder.get_stream_params()  # type: ignore
            .pipe(
                self._stream_url_resolver,
                self._stream_fetcher,
                self._recording_monitor,
                self._dl_statistics,
                self._stream_parser,
                self._connection_error_handler,
                self._request_exception_handler,
                flv_ops.process(sort_tags=True, trace=self._debug),
                self._cutter,
                self._limiter,
                self._join_point_extractor,
                self._prober,
                self._injector,
                self._analyser,
                self._dumper,
                self._rec_statistics,
                self._progress_bar,
                self._exception_handler,
            )
            .subscribe(
                on_completed=self._on_completed,
                scheduler=NewThreadScheduler(self._thread_factory('StreamRecorder')),
            )
        )
