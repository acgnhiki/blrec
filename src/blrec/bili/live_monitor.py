import logging


from .danmaku_client import DanmakuClient, DanmakuListener, DanmakuCommand
from .live import Live
from .typing import Danmaku
from .models import LiveStatus, RoomInfo
from ..event.event_emitter import EventListener, EventEmitter
from ..utils.mixins import SwitchableMixin


__all__ = 'LiveMonitor', 'LiveEventListener'


logger = logging.getLogger(__name__)


class LiveEventListener(EventListener):
    async def on_live_status_changed(
        self, current_status: LiveStatus, previous_status: LiveStatus
    ) -> None:
        ...

    async def on_live_began(self, live: Live) -> None:
        ...

    async def on_live_ended(self, live: Live) -> None:
        ...

    async def on_live_stream_available(self, live: Live) -> None:
        ...

    async def on_live_stream_reset(self, live: Live) -> None:
        ...

    async def on_room_changed(self, room_info: RoomInfo) -> None:
        ...


class LiveMonitor(
    EventEmitter[LiveEventListener], DanmakuListener, SwitchableMixin
):
    def __init__(self, danmaku_client: DanmakuClient, live: Live) -> None:
        super().__init__()
        self._danmaku_client = danmaku_client
        self._live = live

    def _init_status(self) -> None:
        self._previous_status = self._live.room_info.live_status
        if self._live.is_living():
            self._status_count = 2
        else:
            self._status_count = 0

    def _do_enable(self) -> None:
        self._init_status()
        self._danmaku_client.add_listener(self)
        logger.debug('Enabled live monitor')

    def _do_disable(self) -> None:
        self._danmaku_client.remove_listener(self)
        logger.debug('Disabled live monitor')

    async def on_client_reconnected(self) -> None:
        # check the live status after the client reconnected and simulate
        # events if necessary.
        # make sure the recorder works well continuously after interruptions
        # such as an operating system hibernation.
        logger.warning('The Danmaku Client Reconnected')

        await self._live.update_info()
        current_status = self._live.room_info.live_status

        if current_status == self._previous_status:
            return

        if current_status == LiveStatus.LIVE:
            logger.debug('Simulating live began event')
            await self._handle_status_change(current_status)
            logger.debug('Simulating live stream available event')
            await self._handle_status_change(current_status)
        else:
            logger.debug('Simulating live ended event')
            await self._handle_status_change(current_status)

    async def on_danmaku_received(self, danmu: Danmaku) -> None:
        danmu_cmd = danmu['cmd']

        if danmu_cmd == DanmakuCommand.LIVE.value:
            await self._handle_status_change(LiveStatus.LIVE)
        elif danmu_cmd == DanmakuCommand.PREPARING.value:
            if danmu.get('round', None) == 1:
                await self._handle_status_change(LiveStatus.ROUND)
            else:
                await self._handle_status_change(LiveStatus.PREPARING)
        elif danmu_cmd == DanmakuCommand.ROOM_CHANGE.value:
            await self._live.update_room_info()
            await self._emit('room_changed', self._live.room_info)

    async def _handle_status_change(self, current_status: LiveStatus) -> None:
        logger.debug('Live status changed from {} to {}'.format(
            self._previous_status.name, current_status.name
        ))

        await self._live.update_info()
        assert self._live.room_info.live_status == current_status

        await self._emit(
            'live_status_changed', current_status, self._previous_status
        )

        if current_status != LiveStatus.LIVE:
            self._status_count = 0
            await self._emit('live_ended', self._live)
        else:
            self._status_count += 1

            if self._status_count == 1:
                assert self._previous_status != LiveStatus.LIVE
                await self._emit('live_began', self._live)
            elif self._status_count == 2:
                assert self._previous_status == LiveStatus.LIVE
                await self._emit('live_stream_available', self._live)
            elif self._status_count > 2:
                assert self._previous_status == LiveStatus.LIVE
                await self._emit('live_stream_reset', self._live)
            else:
                pass

        logger.debug('Number of sequential LIVE status: {}'.format(
            self._status_count
        ))

        self._previous_status = current_status
