
import asyncio

from .exception_center import ExceptionCenter


__all__ = (
    'ExceptionSubmitter',
    'submit_exception',
    'exception_callback',
)


class ExceptionSubmitter:
    def __enter__(self):  # type: ignore
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        if exc_val is not None:
            submit_exception(exc_val)
        return True


def submit_exception(exc: BaseException) -> None:
    ExceptionCenter.get_instance().submit(exc)


def exception_callback(future: asyncio.Future) -> None:  # type: ignore
    if not future.done() or future.cancelled():
        return
    if (exc := future.exception()):
        submit_exception(exc)
