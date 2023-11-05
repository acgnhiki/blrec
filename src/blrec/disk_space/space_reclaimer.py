import asyncio
import glob
import os
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Iterable, List

from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_none

from ..utils.mixins import SwitchableMixin
from .helpers import delete_file, is_space_enough
from .space_monitor import DiskUsage, SpaceEventListener, SpaceMonitor

__all__ = ('SpaceReclaimer',)


class SpaceReclaimer(SpaceEventListener, SwitchableMixin):
    _SUFFIX_SET = frozenset(
        (
            '.flv',
            '.mp4',
            '.ts',
            '.m4s',
            '.m3u8',
            '.xml',
            '.json',
            '.meta',
            '.jsonl',
            '.jpg',
            '.png',
        )
    )

    def __init__(
        self,
        space_monitor: SpaceMonitor,
        path: str,
        *,
        rec_ttl: int = 60 * 60 * 24,
        recycle_records: bool = False,
    ) -> None:
        super().__init__()
        self._space_monitor = space_monitor
        self.path = path
        if value := os.environ.get('BLREC_REC_TTL'):
            try:
                rec_ttl = int(value)
            except Exception as exc:
                logger.warning(repr(exc))
        self.rec_ttl = rec_ttl
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
        ts = datetime.now().timestamp() - self.rec_ttl
        for path in await self._get_record_file_paths(ts):
            await delete_file(path)
            if is_space_enough(self.path, size):
                return True
        return False

    @retry(
        retry=retry_if_exception_type(OSError),
        wait=wait_none(),
        stop=stop_after_attempt(3),
    )
    async def _get_record_file_paths(self, ts: float) -> List[str]:
        glob_path = os.path.join(self.path, '*/**/*.*')
        paths: Iterable[Path]
        paths = map(lambda p: Path(p), glob.iglob(glob_path, recursive=True))
        paths = filter(lambda p: p.suffix in self._SUFFIX_SET, paths)
        paths = filter(lambda p: p.stat().st_mtime < ts > p.stat().st_atime, paths)
        func = partial(
            sorted, paths, key=lambda p: (p.stat().st_mtime, p.stat().st_atime)
        )
        loop = asyncio.get_running_loop()
        path_list = await loop.run_in_executor(None, func)
        return list(map(str, path_list))
