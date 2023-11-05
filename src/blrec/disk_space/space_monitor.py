import asyncio
import shutil
from contextlib import suppress

from loguru import logger

from ..event.event_emitter import EventEmitter, EventListener
from ..exception import exception_callback
from ..utils.mixins import AsyncStoppableMixin, SwitchableMixin
from .helpers import is_space_enough
from .models import DiskUsage

__all__ = 'SpaceMonitor', 'SpaceEventListener'


class SpaceEventListener(EventListener):
    async def on_space_no_enough(
        self, path: str, threshold: int, disk_usage: DiskUsage
    ) -> None:
        ...


class SpaceMonitor(
    EventEmitter[SpaceEventListener], SwitchableMixin, AsyncStoppableMixin
):
    def __init__(
        self,
        path: str,
        *,
        check_interval: int = 60,  # seconds
        space_threshold: int = 1073741824,  # 1GB
    ) -> None:
        super().__init__()
        self.path = path
        self._check_interval = check_interval
        self.space_threshold = space_threshold
        self._monitoring: bool = False

    @property
    def check_interval(self) -> int:
        return self._check_interval

    @check_interval.setter
    def check_interval(self, value: int) -> None:
        self._check_interval = value
        if value <= 0:
            self.disable()
        else:
            self.enable()

    def _do_enable(self) -> None:
        if self._check_interval <= 0:
            return
        asyncio.create_task(self.start())
        logger.debug('Enabled space monitor')

    def _do_disable(self) -> None:
        asyncio.create_task(self.stop())
        logger.debug('Disabled space monitor')

    async def _do_start(self) -> None:
        self._create_polling_task()

    async def _do_stop(self) -> None:
        await self._cancel_polling_task()

    def _create_polling_task(self) -> None:
        self._polling_task = asyncio.create_task(self._polling_loop())
        self._polling_task.add_done_callback(exception_callback)

    async def _cancel_polling_task(self) -> None:
        self._polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._polling_task

    async def _polling_loop(self) -> None:
        while True:
            if not is_space_enough(self.path, self.space_threshold):
                logger.warning('No enough disk space left')
                await self._emit_space_no_enough()
            await asyncio.sleep(self.check_interval)

    async def _emit_space_no_enough(self) -> None:
        usage = DiskUsage(*shutil.disk_usage(self.path))
        await self._emit('space_no_enough', self.path, self.space_threshold, usage)
