from __future__ import annotations

import asyncio
import logging
from typing import Optional, TypeVar

import requests
import urllib3
from reactivex import Observable, abc

from ...utils import operators as utils_ops

__all__ = ('RequestExceptionHandler',)


logger = logging.getLogger(__name__)

_T = TypeVar('_T')


class RequestExceptionHandler:
    def __call__(self, source: Observable[_T]) -> Observable[_T]:
        return self._handle(source).pipe(
            utils_ops.retry(delay=1, should_retry=self._should_retry)
        )

    def _handle(self, source: Observable[_T]) -> Observable[_T]:
        def subscribe(
            observer: abc.ObserverBase[_T],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            def on_error(exc: Exception) -> None:
                try:
                    raise exc
                except asyncio.exceptions.TimeoutError:
                    logger.warning(repr(exc))
                except requests.exceptions.Timeout:
                    logger.warning(repr(exc))
                except requests.exceptions.HTTPError:
                    logger.warning(repr(exc))
                except urllib3.exceptions.TimeoutError:
                    logger.warning(repr(exc))
                except urllib3.exceptions.ProtocolError:
                    # ProtocolError('Connection broken: IncompleteRead(
                    logger.warning(repr(exc))
                except Exception:
                    pass
                observer.on_error(exc)

            return source.subscribe(
                observer.on_next, on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(
            exc,
            (
                asyncio.exceptions.TimeoutError,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError,
                urllib3.exceptions.TimeoutError,
                urllib3.exceptions.ProtocolError,
            ),
        ):
            return True
        else:
            return False
