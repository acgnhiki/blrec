from __future__ import annotations

import asyncio
import time
from typing import Optional, TypeVar

import aiohttp
import requests
import urllib3
from loguru import logger
from reactivex import Observable, abc
from reactivex import operators as ops

from blrec.core import operators as core_ops
from blrec.utils import operators as utils_ops

__all__ = ('RequestExceptionHandler',)


_T = TypeVar('_T')


class RequestExceptionHandler:
    def __init__(self, stream_url_resolver: core_ops.StreamURLResolver) -> None:
        self._stream_url_resolver = stream_url_resolver
        self._last_retry_time = time.monotonic()

    def __call__(self, source: Observable[_T]) -> Observable[_T]:
        return self._handle(source).pipe(
            ops.do_action(on_error=self._before_retry),
            utils_ops.retry(should_retry=self._should_retry),
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
                except aiohttp.ClientError:
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
                aiohttp.ClientError,
            ),
        ):
            return True
        else:
            return False

    def _before_retry(self, exc: Exception) -> None:
        if isinstance(
            exc, requests.exceptions.HTTPError
        ) and exc.response.status_code in (403, 404):
            self._stream_url_resolver.reset()
            self._stream_url_resolver.rotate_routes()
