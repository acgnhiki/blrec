import logging
from asyncio import Queue, QueueFull
from typing import Final


from .models import DanmuMsg
from ..bili.danmaku_client import (
    DanmakuClient, DanmakuListener, DanmakuCommand
)
from ..bili.typing import Danmaku
from ..utils.mixins import StoppableMixin


__all__ = 'DanmakuReceiver',


logger = logging.getLogger(__name__)


class DanmakuReceiver(DanmakuListener, StoppableMixin):
    _MAX_QUEUE_SIZE: Final[int] = 2000

    def __init__(self, danmaku_client: DanmakuClient) -> None:
        super().__init__()
        self._danmaku_client = danmaku_client
        self._queue: Queue[DanmuMsg] = Queue(maxsize=self._MAX_QUEUE_SIZE)

    def _do_start(self) -> None:
        self._danmaku_client.add_listener(self)
        logger.debug('Started danmaku receiver')

    def _do_stop(self) -> None:
        self._danmaku_client.remove_listener(self)
        self._clear_queue()
        logger.debug('Stopped danmaku receiver')

    async def get_message(self) -> DanmuMsg:
        return await self._queue.get()

    async def on_danmaku_received(self, danmu: Danmaku) -> None:
        if danmu['cmd'] != DanmakuCommand.DANMU_MSG.value:
            return

        danmu_msg = DanmuMsg.from_cmd(danmu)
        try:
            self._queue.put_nowait(danmu_msg)
        except QueueFull:
            self._queue.get_nowait()  # discard the first item
            self._queue.put_nowait(danmu_msg)

    def _clear_queue(self) -> None:
        self._queue = Queue(maxsize=self._MAX_QUEUE_SIZE)
