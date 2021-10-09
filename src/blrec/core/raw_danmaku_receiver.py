import logging
from asyncio import Queue, QueueFull
from typing import Final


from ..bili.danmaku_client import DanmakuClient, DanmakuListener
from ..bili.typing import Danmaku
from ..utils.mixins import StoppableMixin


__all__ = 'RawDanmakuReceiver',


logger = logging.getLogger(__name__)


class RawDanmakuReceiver(DanmakuListener, StoppableMixin):
    _MAX_QUEUE_SIZE: Final[int] = 2000

    def __init__(self, danmaku_client: DanmakuClient) -> None:
        super().__init__()
        self._danmaku_client = danmaku_client
        self._queue: Queue[Danmaku] = Queue(maxsize=self._MAX_QUEUE_SIZE)

    def _do_start(self) -> None:
        self._danmaku_client.add_listener(self)
        logger.debug('Started raw danmaku receiver')

    def _do_stop(self) -> None:
        self._danmaku_client.remove_listener(self)
        self._clear_queue()
        logger.debug('Stopped raw danmaku receiver')

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
