from loguru import logger

from ..utils.mixins import SwitchableMixin
from .exception_center import ExceptionCenter
from .helpers import format_exception

__all__ = ('ExceptionHandler',)


class ExceptionHandler(SwitchableMixin):
    def _do_enable(self) -> None:
        exceptions = ExceptionCenter.get_instance().exceptions
        self._subscription = exceptions.subscribe(self._handle_exception)
        logger.debug('Enabled Exception Handler')

    def _do_disable(self) -> None:
        self._subscription.dispose()
        logger.debug('Disabled Exception Handler')

    def _handle_exception(self, exc: BaseException) -> None:
        self._log_exception(exc)

    def _log_exception(self, exc: BaseException) -> None:
        logger.critical('{}\n{}', repr(exc), format_exception(exc))
