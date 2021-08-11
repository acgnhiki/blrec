import logging
import asyncio
import shutil
from contextlib import suppress


from .models import DiskUsage
from .helpers import is_space_enough
from ..event.event_emitter import EventListener, EventEmitter
from ..exception import exception_callback
from ..utils.mixins import SwitchableMixin
from ..logging.room_id import aio_task_with_room_id


__all__ = 'SpaceMonitor', 'SpaceEventListener'


logger = logging.getLogger(__name__)


class SpaceEventListener(EventListener):
    async def on_space_no_enough(
        self, path: str, threshold: int, disk_usage: DiskUsage
    ) -> None:
        ...


class SpaceMonitor(EventEmitter[SpaceEventListener], SwitchableMixin):
    def __init__(
        self,
        path: str,
        *,
        check_interval: int = 60,  # seconds
        space_threshold: int = 1073741824,  # 1GB
    ) -> None:
        super().__init__()
        self.path = path
        self.check_interval = check_interval
        self.space_threshold = space_threshold
        self._monitoring: bool = False

    def _do_enable(self) -> None:
        asyncio.create_task(self._start())
        logger.debug('Enabled space monitor')

    def _do_disable(self) -> None:
        asyncio.create_task(self._stop())
        logger.debug('Disabled space monitor')

    async def _start(self) -> None:
        if self._monitoring:
            return
        self._create_polling_task()
        self._monitoring = True

    async def _stop(self) -> None:
        if not self._monitoring:
            return
        await self._cancel_polling_task()
        self._monitoring = False

    def _create_polling_task(self) -> None:
        self._polling_task = asyncio.create_task(self._polling_loop())
        self._polling_task.add_done_callback(exception_callback)

    async def _cancel_polling_task(self) -> None:
        self._polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._polling_task

    @aio_task_with_room_id
    async def _polling_loop(self) -> None:
        while True:
            if not is_space_enough(self.path, self.space_threshold):
                logger.warning('No enough disk space left')
                await self._emit_space_no_enough()
            await asyncio.sleep(self.check_interval)

    async def _emit_space_no_enough(self) -> None:
        usage = DiskUsage(*shutil.disk_usage(self.path))
        await self._emit(
            'space_no_enough', self.path, self.space_threshold, usage
        )
