import io
import errno
import logging
from urllib.parse import urlparse

from typing import Optional

import urllib3
import requests
from tqdm import tqdm
from tenacity import (
    retry_if_result,
    retry_if_not_exception_type,
    Retrying,
    TryAgain,
)

from .stream_analyzer import StreamProfile
from .base_stream_recorder import BaseStreamRecorder, StreamProxy
from .retry import wait_exponential_for_same_exceptions, before_sleep_log
from ..bili.live import Live
from ..bili.typing import StreamFormat, QualityNumber
from ..flv.stream_processor import StreamProcessor
from ..utils.mixins import AsyncCooperationMixin, AsyncStoppableMixin
from ..flv.exceptions import FlvDataError, FlvStreamCorruptedError
from ..bili.exceptions import (
    LiveRoomHidden, LiveRoomLocked, LiveRoomEncrypted, NoStreamAvailable,
)


__all__ = 'FLVStreamRecorder',


logger = logging.getLogger(__name__)


class FLVStreamRecorder(
    BaseStreamRecorder,
    AsyncCooperationMixin,
    AsyncStoppableMixin,
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
        super().__init__(
            live=live,
            out_dir=out_dir,
            path_template=path_template,
            stream_format=stream_format,
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

    def _main_loop(self) -> None:
        for attempt in Retrying(
            reraise=True,
            retry=(
                retry_if_result(lambda r: not self._stopped) |
                retry_if_not_exception_type((OSError, NotImplementedError))
            ),
            wait=wait_exponential_for_same_exceptions(max=60),
            before_sleep=before_sleep_log(logger, logging.DEBUG, 'main_loop'),
        ):
            with attempt:
                try:
                    self._streaming_loop()
                except NoStreamAvailable as e:
                    logger.warning(f'No stream available: {repr(e)}')
                    if not self._stopped:
                        raise TryAgain
                except OSError as e:
                    logger.critical(repr(e), exc_info=e)
                    if e.errno == errno.ENOSPC:
                        # OSError(28, 'No space left on device')
                        self._handle_exception(e)
                        self._stopped = True
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
                    self._handle_exception(e)

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
