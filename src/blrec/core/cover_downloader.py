import asyncio
import logging
from enum import Enum
from threading import Lock
from typing import Set

import aiofiles
import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed

from ..bili.live import Live
from ..exception import exception_callback
from ..logging.room_id import aio_task_with_room_id
from ..path import cover_path
from ..utils.hash import sha1sum
from ..utils.mixins import SwitchableMixin
from .stream_recorder import StreamRecorder, StreamRecorderEventListener

__all__ = ('CoverDownloader',)


logger = logging.getLogger(__name__)


class CoverSaveStrategy(Enum):
    DEFAULT = 'default'
    DEDUP = 'dedup'

    def __str__(self) -> str:
        return self.value

    # workaround for value serialization
    def __repr__(self) -> str:
        return str(self)


class CoverDownloader(StreamRecorderEventListener, SwitchableMixin):
    def __init__(
        self,
        live: Live,
        stream_recorder: StreamRecorder,
        *,
        save_cover: bool = False,
        cover_save_strategy: CoverSaveStrategy = CoverSaveStrategy.DEFAULT,
    ) -> None:
        super().__init__()
        self._live = live
        self._stream_recorder = stream_recorder
        self._lock: Lock = Lock()
        self._sha1_set: Set[str] = set()
        self.save_cover = save_cover
        self.cover_save_strategy = cover_save_strategy

    def _do_enable(self) -> None:
        self._sha1_set.clear()
        self._stream_recorder.add_listener(self)
        logger.debug('Enabled cover downloader')

    def _do_disable(self) -> None:
        self._stream_recorder.remove_listener(self)
        logger.debug('Disabled cover downloader')

    async def on_video_file_completed(self, video_path: str) -> None:
        with self._lock:
            if not self.save_cover:
                return
            task = asyncio.create_task(self._save_cover(video_path))
            task.add_done_callback(exception_callback)

    @aio_task_with_room_id
    async def _save_cover(self, video_path: str) -> None:
        try:
            await self._live.update_room_info()
            cover_url = self._live.room_info.cover
            data = await self._fetch_cover(cover_url)
            sha1 = sha1sum(data)
            if (
                self.cover_save_strategy == CoverSaveStrategy.DEDUP
                and sha1 in self._sha1_set
            ):
                return
            path = cover_path(video_path, ext=cover_url.rsplit('.', 1)[-1])
            await self._save_file(path, data)
            self._sha1_set.add(sha1)
        except Exception as e:
            logger.error(f'Failed to save cover image: {repr(e)}')
        else:
            logger.info(f'Saved cover image: {path}')

    @retry(reraise=True, wait=wait_fixed(1), stop=stop_after_attempt(3))
    async def _fetch_cover(self, url: str) -> bytes:
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.get(url) as response:
                return await response.read()

    async def _save_file(self, path: str, data: bytes) -> None:
        async with aiofiles.open(path, 'wb') as file:
            await file.write(data)
