from asyncio import Queue, QueueFull
from typing import Final

from loguru import logger

from blrec.bili.danmaku_client import DanmakuClient, DanmakuListener
from blrec.bili.live import Live
from blrec.bili.typing import Danmaku
from blrec.utils.mixins import StoppableMixin

__all__ = ('RawDanmakuReceiver',)


class RawDanmakuReceiver(DanmakuListener, StoppableMixin):
    _MAX_QUEUE_SIZE: Final[int] = 2000

    def __init__(self, live: Live, danmaku_client: DanmakuClient) -> None:
        super().__init__()
        self._logger = logger.bind(room_id=live.room_id)
        self._danmaku_client = danmaku_client
        self._queue: Queue[Danmaku] = Queue(maxsize=self._MAX_QUEUE_SIZE)

    def _do_start(self) -> None:
        self._danmaku_client.add_listener(self)
        self._logger.debug('Started raw danmaku receiver')

    def _do_stop(self) -> None:
        self._danmaku_client.remove_listener(self)
        self._clear_queue()
        self._logger.debug('Stopped raw danmaku receiver')

    async def get_raw_danmaku(self) -> Danmaku:
        return await self._queue.get()

    async def on_danmaku_received(self, danmu: Danmaku) -> None:
        try:
            self._queue.put_nowait(danmu)
        except QueueFull:
            self._queue.get_nowait()  # discard the first item
            self._queue.put_nowait(danmu)

    def _clear_queue(self) -> None:
        self._queue = Queue(maxsize=self._MAX_QUEUE_SIZE)
