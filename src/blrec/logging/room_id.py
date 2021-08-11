import threading
import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar


_T = TypeVar('_T')


def with_room_id(room_id: int):  # type: ignore
    def decorate(func: Callable[..., _T]) -> Callable[..., _T]:
        @wraps(func)
        def wrapper(*arg: Any, **kwargs: Any) -> _T:
            curr_thread = threading.current_thread()
            old_name = curr_thread.getName()
            curr_thread.setName(f'{func.__qualname__}::{room_id}')
            try:
                return func(*arg, **kwargs)
            finally:
                curr_thread.setName(old_name)
        return wrapper
    return decorate


def aio_task_with_room_id(
    func: Callable[..., Awaitable[_T]]
) -> Callable[..., Awaitable[_T]]:
    @wraps(func)
    async def wrapper(obj: Any, *arg: Any, **kwargs: Any) -> _T:
        if hasattr(obj, '_room_id'):
            room_id = obj._room_id
        elif hasattr(obj, '_live'):
            room_id = obj._live.room_id
        else:
            room_id = ''

        curr_task = asyncio.current_task()
        assert curr_task is not None
        curr_task.set_name(f'{func.__qualname__}::{room_id}')

        return await func(obj, *arg, **kwargs)

    return wrapper
