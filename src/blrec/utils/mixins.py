from abc import ABC, abstractmethod
import asyncio
from typing import Awaitable, TypeVar, final


class SwitchableMixin(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @final
    def enable(self) -> None:
        if self._enabled:
            return
        self._enabled = True
        self._do_enable()

    @final
    def disable(self) -> None:
        if not self._enabled:
            return
        self._enabled = False
        self._do_disable()

    @abstractmethod
    def _do_enable(self) -> None:
        ...

    @abstractmethod
    def _do_disable(self) -> None:
        ...


class StoppableMixin(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._stopped = True

    @property
    def stopped(self) -> bool:
        return self._stopped

    @final
    def start(self) -> None:
        if not self._stopped:
            return
        self._stopped = False
        self._do_start()

    @final
    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._do_stop()

    @abstractmethod
    def _do_start(self) -> None:
        ...

    @abstractmethod
    def _do_stop(self) -> None:
        ...


class AsyncStoppableMixin(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._stopped = True

    @property
    def stopped(self) -> bool:
        return self._stopped

    @final
    async def start(self) -> None:
        if not self._stopped:
            return
        self._stopped = False
        await self._do_start()

    @final
    async def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        await self._do_stop()

    @abstractmethod
    async def _do_start(self) -> None:
        ...

    @abstractmethod
    async def _do_stop(self) -> None:
        ...


_T = TypeVar('_T')


class AsyncCooperationMix(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._loop = asyncio.get_running_loop()

    def _handle_exception(self, exc: BaseException) -> None:
        from ..exception import submit_exception  # XXX circular import

        async def wrapper() -> None:
            submit_exception(exc)
        self._run_coroutine(wrapper())

    def _run_coroutine(self, coro: Awaitable[_T]) -> _T:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()
