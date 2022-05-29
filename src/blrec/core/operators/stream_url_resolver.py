from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

import requests
import urllib3
from reactivex import Observable, abc
from reactivex import operators as ops

from ...bili.exceptions import (
    LiveRoomEncrypted,
    LiveRoomHidden,
    LiveRoomLocked,
    NoAlternativeStreamAvailable,
    NoStreamAvailable,
    NoStreamCodecAvailable,
    NoStreamFormatAvailable,
    NoStreamQualityAvailable,
)
from ...bili.live import Live
from ...utils import operators as utils_ops
from ...utils.mixins import AsyncCooperationMixin
from ..stream_param_holder import StreamParamHolder, StreamParams

__all__ = ('StreamURLResolver',)


logger = logging.getLogger(__name__)
logging.getLogger(urllib3.__name__).setLevel(logging.WARNING)


class StreamURLResolver(AsyncCooperationMixin):
    def __init__(self, live: Live, stream_param_holder: StreamParamHolder) -> None:
        super().__init__()
        self._live = live
        self._stream_param_holder = stream_param_holder
        self._stream_url: str = ''
        self._stream_host: str = ''
        self._stream_params: Optional[StreamParams] = None

    @property
    def stream_url(self) -> str:
        return self._stream_url

    @property
    def stream_host(self) -> str:
        return self._stream_host

    def _reset(self) -> None:
        self._stream_url = ''
        self._stream_host = ''
        self._stream_params = None

    def __call__(self, source: Observable[StreamParams]) -> Observable[str]:
        self._reset()
        return self._solve(source).pipe(
            ops.do_action(on_error=self._before_retry),
            utils_ops.retry(delay=1, should_retry=self._should_retry),
        )

    def _solve(self, source: Observable[StreamParams]) -> Observable[str]:
        def subscribe(
            observer: abc.ObserverBase[str],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            def on_next(params: StreamParams) -> None:
                if self._can_resue_url(params):
                    observer.on_next(self._stream_url)
                    return

                try:
                    logger.info(
                        f'Getting the live stream url... '
                        f'qn: {params.quality_number}, '
                        f'format: {params.stream_format}, '
                        f'api platform: {params.api_platform}, '
                        f'use alternative stream: {params.use_alternative_stream}'
                    )
                    url = self._run_coroutine(
                        self._live.get_live_stream_url(
                            params.quality_number,
                            api_platform=params.api_platform,
                            stream_format=params.stream_format,
                            select_alternative=params.use_alternative_stream,
                        )
                    )
                except Exception as e:
                    logger.warning(f'Failed to get live stream url: {repr(e)}')
                    observer.on_error(e)
                else:
                    logger.info(f"Got live stream url: '{url}'")
                    self._stream_url = url
                    self._stream_host = urlparse(url).hostname or ''
                    self._stream_params = params
                    observer.on_next(url)

            return source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    def _can_resue_url(self, params: StreamParams) -> bool:
        if params == self._stream_params and self._stream_url:
            try:
                response = requests.get(
                    self._stream_url, stream=True, headers=self._live.headers
                )
                response.raise_for_status()
            except Exception:
                return False
            else:
                return True
        else:
            return False

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(
            exc,
            (
                NoStreamAvailable,
                NoStreamCodecAvailable,
                NoStreamFormatAvailable,
                NoStreamQualityAvailable,
                NoAlternativeStreamAvailable,
            ),
        ):
            return True
        else:
            return False

    def _before_retry(self, exc: Exception) -> None:
        try:
            raise exc
        except (NoStreamAvailable, NoStreamCodecAvailable, NoStreamFormatAvailable):
            pass
        except NoStreamQualityAvailable:
            qn = self._stream_param_holder.quality_number
            logger.info(
                f'The specified stream quality ({qn}) is not available, '
                'will using the original stream quality (10000) instead.'
            )
            self._stream_param_holder.fall_back_quality()
        except NoAlternativeStreamAvailable:
            logger.debug(
                'No alternative stream url available, '
                'will using the primary stream url instead.'
            )
            self._stream_param_holder.use_alternative_stream = False
            self._stream_param_holder.rotate_api_platform()
        except LiveRoomHidden:
            pass
        except LiveRoomLocked:
            pass
        except LiveRoomEncrypted:
            pass
        except Exception:
            pass
