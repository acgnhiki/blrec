from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from loguru import logger

_T = TypeVar('_T')

__all__ = ('async_task_with_logger_context',)


def async_task_with_logger_context(
    func: Callable[..., Awaitable[_T]]
) -> Callable[..., Awaitable[_T]]:
    @wraps(func)
    async def wrapper(obj: Any, *arg: Any, **kwargs: Any) -> _T:
        with logger.contextualize(**obj._logger_context):
            return await func(obj, *arg, **kwargs)

    return wrapper
