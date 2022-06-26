from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, TypeVar

import requests
import urllib3
from reactivex import Observable, abc

from ...utils import operators as utils_ops

__all__ = ('RequestExceptionHandler',)


logger = logging.getLogger(__name__)

_T = TypeVar('_T')


class RequestExceptionHandler:
    def __init__(self) -> None:
        self._last_retry_time = time.monotonic()

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
                except requests.exceptions.RequestException:  # XXX: ConnectionError
                    logger.warning(repr(exc))
                except urllib3.exceptions.HTTPError:
                    logger.warning(repr(exc))
                except asyncio.exceptions.TimeoutError:
                    logger.warning(repr(exc))
                except Exception:
                    pass

                if self._should_retry(exc):
                    if time.monotonic() - self._last_retry_time < 1:
                        time.sleep(1)
                    self._last_retry_time = time.monotonic()

                observer.on_error(exc)

            return source.subscribe(
                observer.on_next, on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(
            exc,
            (
                requests.exceptions.RequestException,  # XXX: ConnectionError
                urllib3.exceptions.HTTPError,
                asyncio.exceptions.TimeoutError,
            ),
        ):
            return True
        else:
            return False
