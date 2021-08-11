import logging


from .exception_center import ExceptionCenter
from ..utils.mixins import SwitchableMixin


logger = logging.getLogger(__name__)


__all__ = 'ExceptionHandler',


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
        exc_info = (type(exc), exc, exc.__traceback__)
        msg = 'Unhandled Exception'
        logger.critical(msg, exc_info=exc_info)
