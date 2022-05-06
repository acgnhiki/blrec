import io
import logging
from typing import Optional
from urllib.parse import urlparse

import requests
import urllib3
from tenacity import TryAgain
from tqdm import tqdm

from ..bili.live import Live
from ..bili.typing import QualityNumber
from ..flv.exceptions import FlvDataError, FlvStreamCorruptedError
from ..flv.stream_processor import StreamProcessor
from .stream_analyzer import StreamProfile
from .stream_recorder_impl import StreamProxy, StreamRecorderImpl

__all__ = 'FLVStreamRecorderImpl',


logger = logging.getLogger(__name__)


class FLVStreamRecorderImpl(StreamRecorderImpl):
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

    def _run(self) -> None:
        logger.debug('Stream recorder thread started')
        try:
            with tqdm(
                desc='Recording',
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                postfix=self._make_pbar_postfix(),
            ) as progress_bar:
                self._progress_bar = progress_bar

                self._stream_processor = StreamProcessor(
                    self._file_manager,
                    filesize_limit=self._filesize_limit,
                    duration_limit=self._duration_limit,
                    analyse_data=True,
                    dedup_join=True,
                    save_extra_metadata=True,
                    backup_timestamp=True,
                )

                def update_size(size: int) -> None:
                    progress_bar.update(size)
                    self._rec_calculator.submit(size)

                def update_stream_profile(profile: StreamProfile) -> None:
                    self._stream_profile = profile

                self._stream_processor.size_updates.subscribe(update_size)
                self._stream_processor.stream_profile_updates.subscribe(
                    update_stream_profile
                )

                with requests.Session() as self._session:
                    self._main_loop()
        except TryAgain:
            pass
        except Exception as e:
            self._handle_exception(e)
        finally:
            self._stopped = True
            if self._stream_processor is not None:
                self._stream_processor.finalize()
                self._stream_processor = None
            self._progress_bar = None
            self._dl_calculator.freeze()
            self._rec_calculator.freeze()
            self._emit_event('stream_recording_stopped')
            logger.debug('Stream recorder thread stopped')

    def _streaming_loop(self) -> None:
        url = self._get_live_stream_url()

        while not self._stopped:
            try:
                self._streaming(url)
            except requests.exceptions.HTTPError as e:
                # frequently occurred when the live just started or ended.
                logger.warning(repr(e))
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
                self._wait_for_connection_error()
            except (FlvDataError, FlvStreamCorruptedError) as e:
                logger.warning(repr(e))
                if not self._use_alternative_stream:
                    self._use_alternative_stream = True
                else:
                    self._rotate_api_platform()
                url = self._get_live_stream_url()

    def _streaming(self, url: str) -> None:
        logger.debug(f'Requesting live stream... {url}')
        self._stream_url = url
        self._stream_host = urlparse(url).hostname or ''

        with self._session.get(
            url,
            stream=True,
            headers=self._live.headers,
            timeout=self.read_timeout,
        ) as response:
            logger.debug('Response received')
            response.raise_for_status()

            if self._stopped:
                return

            assert self._stream_processor is not None
            self._stream_processor.set_metadata(self._make_metadata())

            stream_proxy = StreamProxy(response.raw)
            stream_proxy.size_updates.subscribe(
                lambda n: self._dl_calculator.submit(n)
            )

            self._stream_processor.process_stream(
                io.BufferedReader(stream_proxy, buffer_size=8192)
            )
