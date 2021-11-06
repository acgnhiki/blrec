import logging
from asyncio import Queue, QueueFull
from typing import Final


from .models import DanmuMsg, GiftSendMsg, GuardBuyMsg, SuperChatMsg
from .typing import DanmakuMsg
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
        self._queue: Queue[DanmakuMsg] = Queue(maxsize=self._MAX_QUEUE_SIZE)

    def _do_start(self) -> None:
        self._danmaku_client.add_listener(self)
        logger.debug('Started danmaku receiver')

    def _do_stop(self) -> None:
        self._danmaku_client.remove_listener(self)
        self._clear_queue()
        logger.debug('Stopped danmaku receiver')

    async def get_message(self) -> DanmakuMsg:
        return await self._queue.get()

    async def on_danmaku_received(self, danmu: Danmaku) -> None:
        cmd = danmu['cmd']
        msg: DanmakuMsg

        if cmd == DanmakuCommand.DANMU_MSG.value:
            msg = DanmuMsg.from_danmu(danmu)
        elif cmd == DanmakuCommand.SEND_GIFT.value:
            msg = GiftSendMsg.from_danmu(danmu)
        elif cmd == DanmakuCommand.GUARD_BUY.value:
            msg = GuardBuyMsg.from_danmu(danmu)
        elif cmd == DanmakuCommand.SUPER_CHAT_MESSAGE.value:
            msg = SuperChatMsg.from_danmu(danmu)
        else:
            return

        try:
            self._queue.put_nowait(msg)
        except QueueFull:
            self._queue.get_nowait()  # discard the first item
            self._queue.put_nowait(msg)

    def _clear_queue(self) -> None:
        self._queue = Queue(maxsize=self._MAX_QUEUE_SIZE)
