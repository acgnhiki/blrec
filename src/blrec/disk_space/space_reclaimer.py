import os
import glob
from datetime import datetime
from pathlib import Path
import logging
import asyncio
from functools import partial
from typing import Iterable, List


from .helpers import delete_file, is_space_enough
from .space_monitor import SpaceMonitor, DiskUsage, SpaceEventListener
from ..utils.mixins import SwitchableMixin


__all__ = 'SpaceReclaimer',


logger = logging.getLogger(__name__)


class SpaceReclaimer(SpaceEventListener, SwitchableMixin):
    _SUFFIX_SET = frozenset(('.flv', '.mp4', '.xml', '.meta'))

    def __init__(
        self,
        space_monitor: SpaceMonitor,
        path: str,
        *,
        recycle_records: bool = False,
    ) -> None:
        super().__init__()
        self._space_monitor = space_monitor
        self.path = path
        self.recycle_records = recycle_records

    async def on_space_no_enough(
        self, path: str, threshold: int, disk_usage: DiskUsage
    ) -> None:
        await self._free_space(threshold)

    def _do_enable(self) -> None:
        self._space_monitor.add_listener(self)
        logger.debug('Enabled space reclaimer')

    def _do_disable(self) -> None:
        self._space_monitor.remove_listener(self)
        logger.debug('Disabled space reclaimer')

    async def _free_space(self, size: int) -> bool:
        if is_space_enough(self.path, size):
            return True
        if self.recycle_records:
            if await self._free_space_from_records(size):
                return True
        return False

    async def _free_space_from_records(self, size: int) -> bool:
        logger.info('Free space from records ...')
        # only delete files created 24 hours ago
        max_ctime = datetime.now().timestamp() - 60 * 60 * 24
        for path in await self._get_record_file_paths(max_ctime):
            await delete_file(path)
            if is_space_enough(self.path, size):
                return True
        return False

    async def _get_record_file_paths(self, max_ctime: float) -> List[str]:
        glob_path = os.path.join(self.path, '*/**/*.*')
        paths: Iterable[Path]
        paths = map(lambda p: Path(p), glob.iglob(glob_path, recursive=True))
        paths = filter(lambda p: p.suffix in self._SUFFIX_SET, paths)
        paths = filter(lambda p: p.stat().st_ctime <= max_ctime, paths)
        func = partial(sorted, paths, key=lambda p: p.stat().st_ctime)
        loop = asyncio.get_running_loop()
        path_list = await loop.run_in_executor(None, func)
        return list(map(str, path_list))
