from __future__ import annotations

import errno
import logging
from typing import Optional, TypeVar

from reactivex import Observable, abc

from ...bili.exceptions import LiveRoomEncrypted, LiveRoomHidden, LiveRoomLocked
from ...utils import operators as utils_ops
from ...utils.mixins import AsyncCooperationMixin

__all__ = ('ExceptionHandler',)


logger = logging.getLogger(__name__)

_T = TypeVar('_T')


class ExceptionHandler(AsyncCooperationMixin):
    def __call__(self, source: Observable[_T]) -> Observable[_T]:
        return self._handle(source).pipe(utils_ops.retry(delay=1))

    def _handle(self, source: Observable[_T]) -> Observable[_T]:
        def subscribe(
            observer: abc.ObserverBase[_T],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            def on_error(exc: Exception) -> None:
                logger.exception(repr(exc))
                self._submit_exception(exc)
                try:
                    raise exc
                except OSError as e:
                    logger.critical(repr(e), exc_info=e)
                    if e.errno == errno.ENOSPC:
                        # OSError(28, 'No space left on device')
                        observer.on_completed()
                    else:
                        observer.on_error(exc)
                except LiveRoomHidden:
                    logger.error('The live room has been hidden!')
                    observer.on_completed()
                except LiveRoomLocked:
                    logger.error('The live room has been locked!')
                    observer.on_completed()
                except LiveRoomEncrypted:
                    logger.error('The live room has been encrypted!')
                    observer.on_completed()
                except Exception:
                    observer.on_error(exc)

            return source.subscribe(
                observer.on_next, on_error, observer.on_completed, scheduler=scheduler
            )

        return Observable(subscribe)
