import asyncio
import random
from contextlib import suppress

from loguru import logger

from blrec.exception import exception_callback
from blrec.logging.context import async_task_with_logger_context

from ..event.event_emitter import EventEmitter, EventListener
from ..utils.mixins import SwitchableMixin
from .danmaku_client import DanmakuClient, DanmakuCommand, DanmakuListener
from .helpers import extract_formats
from .live import Live
from .models import LiveStatus, RoomInfo
from .typing import Danmaku

__all__ = 'LiveMonitor', 'LiveEventListener'


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


class LiveMonitor(EventEmitter[LiveEventListener], DanmakuListener, SwitchableMixin):
    def __init__(self, danmaku_client: DanmakuClient, live: Live) -> None:
        super().__init__()
        self._logger_context = {'room_id': live.room_id}
        self._logger = logger.bind(**self._logger_context)
        self._danmaku_client = danmaku_client
        self._live = live

    def _init_status(self) -> None:
        self._previous_status = self._live.room_info.live_status
        if self._live.is_living():
            self._status_count = 2
            self._stream_available = True
        else:
            self._status_count = 0
            self._stream_available = False

    def _do_enable(self) -> None:
        self._init_status()
        self._danmaku_client.add_listener(self)
        self._start_polling()
        self._logger.debug('Enabled live monitor')

    def _do_disable(self) -> None:
        self._danmaku_client.remove_listener(self)
        asyncio.create_task(self._stop_polling())
        asyncio.create_task(self._stop_checking())
        self._logger.debug('Disabled live monitor')

    def _start_polling(self) -> None:
        self._polling_task = asyncio.create_task(self._poll_live_status())
        self._polling_task.add_done_callback(exception_callback)

    async def _stop_polling(self) -> None:
        self._polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._polling_task
        del self._polling_task

    def _start_checking(self) -> None:
        self._checking_task = asyncio.create_task(self._check_if_stream_available())
        self._checking_task.add_done_callback(exception_callback)
        asyncio.get_running_loop().call_later(
            1800, lambda: asyncio.create_task(self._stop_checking())
        )

    async def _stop_checking(self) -> None:
        if not hasattr(self, '_checking_task'):
            return
        self._checking_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._checking_task
        del self._checking_task

    async def on_client_reconnected(self) -> None:
        # check the live status after the client reconnected and simulate
        # events if necessary.
        # make sure the recorder works well continuously after interruptions
        # such as an operating system hibernation.
        self._logger.warning('The Danmaku Client Reconnected')

        await self._live.update_room_info()
        current_status = self._live.room_info.live_status

        if current_status == self._previous_status:
            if current_status == LiveStatus.LIVE:
                self._logger.debug('Simulating stream reset event')
                await self._handle_status_change(current_status)
        else:
            if current_status == LiveStatus.LIVE:
                self._logger.debug('Simulating live began event')
                await self._handle_status_change(current_status)
                self._logger.debug('Simulating live stream available event')
                await self._handle_status_change(current_status)
            else:
                self._logger.debug('Simulating live ended event')
                await self._handle_status_change(current_status)

    async def on_danmaku_received(self, danmu: Danmaku) -> None:
        danmu_cmd = danmu['cmd']

        if danmu_cmd == DanmakuCommand.LIVE.value:
            await self._live.update_room_info()
            await self._handle_status_change(LiveStatus.LIVE)
        elif danmu_cmd == DanmakuCommand.PREPARING.value:
            await self._live.update_room_info()
            if danmu.get('round', None) == 1:
                await self._handle_status_change(LiveStatus.ROUND)
            else:
                await self._handle_status_change(LiveStatus.PREPARING)
        elif danmu_cmd == DanmakuCommand.ROOM_CHANGE.value:
            await self._live.update_room_info()
            await self._emit('room_changed', self._live.room_info)

    async def _handle_status_change(self, current_status: LiveStatus) -> None:
        self._logger.debug(
            'Live status changed from {} to {}'.format(
                self._previous_status.name, current_status.name
            )
        )

        await self._emit('live_status_changed', current_status, self._previous_status)

        if current_status != LiveStatus.LIVE:
            self._status_count = 0
            self._stream_available = False
            await self._emit('live_ended', self._live)
            await self._stop_checking()
        else:
            self._status_count += 1

            if self._status_count == 1:
                assert self._previous_status != LiveStatus.LIVE
                await self._emit('live_began', self._live)
                self._start_checking()
            elif self._status_count == 2:
                assert self._previous_status == LiveStatus.LIVE
            elif self._status_count > 2:
                assert self._previous_status == LiveStatus.LIVE
                await self._emit('live_stream_reset', self._live)
            else:
                pass

        self._logger.debug(
            'Number of sequential LIVE status: {}'.format(self._status_count)
        )

        self._previous_status = current_status

    async def check_live_status(self) -> None:
        self._logger.debug('Checking live status...')
        try:
            await self._check_live_status()
        except Exception as e:
            self._logger.warning(f'Failed to check live status: {repr(e)}')
        self._logger.debug('Done checking live status')

    async def _check_live_status(self) -> None:
        await self._live.update_room_info()
        current_status = self._live.room_info.live_status
        if current_status != self._previous_status:
            await self._handle_status_change(current_status)

    @async_task_with_logger_context
    async def _poll_live_status(self) -> None:
        self._logger.debug('Started polling live status')

        while True:
            try:
                await asyncio.sleep(600 + random.randrange(-60, 60))
                await self._check_live_status()
            except asyncio.CancelledError:
                self._logger.debug('Cancelled polling live status')
                break
            except Exception as e:
                self._logger.warning(f'Failed to poll live status: {repr(e)}')

        self._logger.debug('Stopped polling live status')

    @async_task_with_logger_context
    async def _check_if_stream_available(self) -> None:
        self._logger.debug('Started checking if stream available')

        while True:
            try:
                streams = await self._live.get_live_streams()
                if streams:
                    self._logger.debug('live stream available')
                    self._stream_available = True
                    flv_formats = extract_formats(streams, 'flv')
                    self._live._no_flv_stream = not flv_formats
                    await self._emit('live_stream_available', self._live)
                    break
            except asyncio.CancelledError:
                self._logger.debug('Cancelled checking if stream available')
                break
            except Exception as e:
                self._logger.warning(f'Failed to check if stream available: {repr(e)}')

            await asyncio.sleep(1)

        self._logger.debug('Stopped checking if stream available')
