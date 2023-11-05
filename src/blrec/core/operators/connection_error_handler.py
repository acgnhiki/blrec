from __future__ import annotations

import time
from typing import Optional, TypeVar

import aiohttp
import requests
from loguru import logger
from reactivex import Observable, abc

from blrec.bili.live import Live
from blrec.utils import operators as utils_ops
from blrec.utils.mixins import AsyncCooperationMixin

__all__ = ('ConnectionErrorHandler',)


_T = TypeVar('_T')


class ConnectionErrorHandler(AsyncCooperationMixin):
    def __init__(
        self,
        live: Live,
        *,
        disconnection_timeout: Optional[int] = None,
        check_interval: int = 3,
    ) -> None:
        super().__init__()
        self._live = live
        self.disconnection_timeout = disconnection_timeout or 600  # seconds
        self.check_interval = check_interval

    def __call__(self, source: Observable[_T]) -> Observable[_T]:
        return self._handle(source).pipe(
            utils_ops.retry(should_retry=self._should_retry)
        )

    def _handle(self, source: Observable[_T]) -> Observable[_T]:
        def subscribe(
            observer: abc.ObserverBase[_T],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            def on_error(exc: Exception) -> None:
                try:
                    raise exc
                except (
                    aiohttp.ClientConnectionError,
                    requests.exceptions.ConnectionError,
                ) as e:
                    logger.warning(repr(e))
                    if self._wait_for_connection_error():
                        observer.on_error(exc)
                    else:
                        observer.on_completed()
                except Exception:
                    pass
                observer.on_error(exc)

            return source.subscribe(
                observer.on_next, on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(
            exc, (aiohttp.ClientConnectionError, requests.exceptions.ConnectionError)
        ):
            return True
        else:
            return False

    def _wait_for_connection_error(self) -> bool:
        timeout = self.disconnection_timeout
        logger.info(f'Waiting {timeout} seconds for connection recovery... ')
        timebase = time.monotonic()
        while not self._call_coroutine(self._live.check_connectivity()):
            if timeout is not None and time.monotonic() - timebase > timeout:
                logger.error(f'Connection not recovered in {timeout} seconds')
                return False
            time.sleep(self.check_interval)
        else:
            logger.info('Connection recovered')
            return True
