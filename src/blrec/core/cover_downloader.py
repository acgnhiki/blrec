from enum import Enum
from threading import Lock
from typing import Set

import aiofiles
import aiohttp
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from blrec.bili.live import Live
from blrec.bili.net import connector, timeout
from blrec.event.event_emitter import EventEmitter, EventListener
from blrec.exception import submit_exception
from blrec.path import cover_path
from blrec.utils.hash import sha1sum
from blrec.utils.mixins import SwitchableMixin

from .stream_recorder import StreamRecorder, StreamRecorderEventListener

__all__ = 'CoverDownloader', 'CoverDownloaderEventListener'


class CoverDownloaderEventListener(EventListener):
    async def on_cover_image_downloaded(self, path: str) -> None: ...


class CoverSaveStrategy(Enum):
    DEFAULT = 'default'
    DEDUP = 'dedup'

    def __str__(self) -> str:
        return self.value

    # workaround for value serialization
    def __repr__(self) -> str:
        return str(self)


class CoverDownloader(
    EventEmitter[CoverDownloaderEventListener],
    StreamRecorderEventListener,
    SwitchableMixin,
):
    def __init__(
        self,
        live: Live,
        stream_recorder: StreamRecorder,
        *,
        save_cover: bool = False,
        cover_save_strategy: CoverSaveStrategy = CoverSaveStrategy.DEFAULT,
    ) -> None:
        super().__init__()
        self._logger_context = {'room_id': live.room_id}
        self._logger = logger.bind(**self._logger_context)
        self._live = live
        self._stream_recorder = stream_recorder
        self._lock: Lock = Lock()
        self._sha1_set: Set[str] = set()
        self.save_cover = save_cover
        self.cover_save_strategy = cover_save_strategy

    def _do_enable(self) -> None:
        self._sha1_set.clear()
        self._stream_recorder.add_listener(self)
        self._logger.debug('Enabled cover downloader')

    def _do_disable(self) -> None:
        self._stream_recorder.remove_listener(self)
        self._logger.debug('Disabled cover downloader')

    async def on_video_file_completed(self, video_path: str) -> None:
        with self._lock:
            if not self.save_cover:
                return
            await self._save_cover(video_path)

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
            self._logger.error(f'Failed to save cover image: {repr(e)}')
            submit_exception(e)
        else:
            self._logger.info(f'Saved cover image: {path}')
            await self._emit('cover_image_downloaded', path)

    @retry(reraise=True, wait=wait_fixed(1), stop=stop_after_attempt(3))
    async def _fetch_cover(self, url: str) -> bytes:
        async with aiohttp.ClientSession(
            connector=connector,
            connector_owner=False,
            raise_for_status=True,
            trust_env=True,
            timeout=timeout,
        ) as session:
            async with session.get(url) as response:
                return await response.read()

    async def _save_file(self, path: str, data: bytes) -> None:
        async with aiofiles.open(path, 'wb') as file:
            await file.write(data)
