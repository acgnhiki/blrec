import atexit
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _TimeoutError
from typing import Callable, Any, Iterable, Mapping, TypeVar


_T = TypeVar('_T')


_executor = None


def wait_for(
    func: Callable[..., _T],
    *,
    args: Iterable[Any] = [],
    kwargs: Mapping[str, Any] = {},
    timeout: float
) -> _T:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=200, thread_name_prefix='wait_for')
        atexit.register(_executor.shutdown)

    future = _executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except _TimeoutError:
        raise TimeoutError(timeout, func, args, kwargs) from None
