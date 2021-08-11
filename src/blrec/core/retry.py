import logging
from typing import Any, Callable, Optional, Type, cast

from tenacity import wait_exponential, RetryCallState
from tenacity import _utils
from tenacity import compat as _compat


class wait_exponential_for_same_exceptions(wait_exponential):
    """Wait strategy that applies exponential backoff only for same
    continuing exceptions.
    """

    def __init__(
        self,
        multiplier: float = 1,
        max: float = _utils.MAX_WAIT,
        exp_base: int = 2,
        min: float = 0,
        continuing_criteria: float = 5.0,
    ) -> None:
        super().__init__(multiplier, max, exp_base, min)
        self._continuing_criteria = continuing_criteria
        self._prev_exc_type: Optional[Type[BaseException]] = None
        self._prev_exc_ts: Optional[float] = None
        self._last_wait_time: float = 0

    @_compat.wait_dunder_call_accept_old_params
    def __call__(self, retry_state: RetryCallState) -> float:
        if (
            retry_state.outcome is not None and
            (exc := retry_state.outcome.exception())
        ):
            curr_exc_type = type(exc)
            curr_exc_ts = cast(float, retry_state.outcome_timestamp)
            if (
                curr_exc_type is not self._prev_exc_type or
                not self._is_continuing(curr_exc_ts)
            ):
                retry_state.attempt_number = 1
                self._prev_exc_type = curr_exc_type
                self._prev_exc_ts = curr_exc_ts

        self._last_wait_time = wait_time = super().__call__(retry_state)
        return wait_time

    def _is_continuing(self, curr_exc_ts: float) -> bool:
        assert self._prev_exc_ts is not None
        return (
            curr_exc_ts - (self._prev_exc_ts + self._last_wait_time) <
            self._continuing_criteria
        )


def before_sleep_log(
    logger: logging.Logger, log_level: int, name: str = ''
) -> Callable[[RetryCallState], Any]:
    def log_it(retry_state: RetryCallState) -> None:
        seconds = cast(float, getattr(retry_state.next_action, 'sleep'))
        logger.log(log_level, 'Retry %s after %s seconds', name, seconds)

    return log_it
