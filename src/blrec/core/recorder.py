from __future__ import annotations
import logging
from datetime import datetime
from typing import Iterator, Optional

import aiohttp
import aiofiles
import humanize
from tenacity import retry, wait_fixed, stop_after_attempt

from .danmaku_receiver import DanmakuReceiver
from .danmaku_dumper import DanmakuDumper, DanmakuDumperEventListener
from .raw_danmaku_receiver import RawDanmakuReceiver
from .raw_danmaku_dumper import RawDanmakuDumper, RawDanmakuDumperEventListener
from .stream_recorder import StreamRecorder, StreamRecorderEventListener
from ..event.event_emitter import EventListener, EventEmitter
from ..bili.live import Live
from ..bili.models import RoomInfo
from ..bili.danmaku_client import DanmakuClient
from ..bili.live_monitor import LiveMonitor, LiveEventListener
from ..bili.typing import QualityNumber
from ..utils.mixins import AsyncStoppableMixin
from ..path import cover_path
from ..logging.room_id import aio_task_with_room_id


__all__ = 'RecorderEventListener', 'Recorder'


logger = logging.getLogger(__name__)


class RecorderEventListener(EventListener):
    async def on_recording_started(self, recorder: Recorder) -> None:
        ...

    async def on_recording_finished(self, recorder: Recorder) -> None:
        ...

    async def on_recording_cancelled(self, recorder: Recorder) -> None:
        ...

    async def on_video_file_created(
        self, recorder: Recorder, path: str
    ) -> None:
        ...

    async def on_video_file_completed(
        self, recorder: Recorder, path: str
    ) -> None:
        ...

    async def on_danmaku_file_created(
        self, recorder: Recorder, path: str
    ) -> None:
        ...

    async def on_danmaku_file_completed(
        self, recorder: Recorder, path: str
    ) -> None:
        ...

    async def on_raw_danmaku_file_created(
        self, recorder: Recorder, path: str
    ) -> None:
        ...

    async def on_raw_danmaku_file_completed(
        self, recorder: Recorder, path: str
    ) -> None:
        ...


class Recorder(
    EventEmitter[RecorderEventListener],
    LiveEventListener,
    AsyncStoppableMixin,
    DanmakuDumperEventListener,
    RawDanmakuDumperEventListener,
    StreamRecorderEventListener,
):
    def __init__(
        self,
        live: Live,
        danmaku_client: DanmakuClient,
        live_monitor: LiveMonitor,
        out_dir: str,
        path_template: str,
        *,
        buffer_size: Optional[int] = None,
        read_timeout: Optional[int] = None,
        disconnection_timeout: Optional[int] = None,
        danmu_uname: bool = False,
        record_gift_send: bool = False,
        record_free_gifts: bool = False,
        record_guard_buy: bool = False,
        record_super_chat: bool = False,
        save_cover: bool = False,
        save_raw_danmaku: bool = False,
        filesize_limit: int = 0,
        duration_limit: int = 0,
    ) -> None:
        super().__init__()

        self._live = live
        self._danmaku_client = danmaku_client
        self._live_monitor = live_monitor
        self.save_cover = save_cover
        self.save_raw_danmaku = save_raw_danmaku

        self._recording: bool = False

        self._stream_recorder = StreamRecorder(
            self._live,
            out_dir=out_dir,
            path_template=path_template,
            buffer_size=buffer_size,
            read_timeout=read_timeout,
            disconnection_timeout=disconnection_timeout,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )

        self._danmaku_receiver = DanmakuReceiver(danmaku_client)
        self._danmaku_dumper = DanmakuDumper(
            self._live,
            self._stream_recorder,
            self._danmaku_receiver,
            danmu_uname=danmu_uname,
            record_gift_send=record_gift_send,
            record_free_gifts=record_free_gifts,
            record_guard_buy=record_guard_buy,
            record_super_chat=record_super_chat,
        )
        self._raw_danmaku_receiver = RawDanmakuReceiver(danmaku_client)
        self._raw_danmaku_dumper = RawDanmakuDumper(
            self._stream_recorder,
            self._raw_danmaku_receiver,
        )

    @property
    def live(self) -> Live:
        return self._live

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def quality_number(self) -> QualityNumber:
        return self._stream_recorder.quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._stream_recorder.quality_number = value

    @property
    def real_quality_number(self) -> QualityNumber:
        return self._stream_recorder.real_quality_number

    @property
    def buffer_size(self) -> int:
        return self._stream_recorder.buffer_size

    @buffer_size.setter
    def buffer_size(self, value: int) -> None:
        self._stream_recorder.buffer_size = value

    @property
    def read_timeout(self) -> int:
        return self._stream_recorder.read_timeout

    @read_timeout.setter
    def read_timeout(self, value: int) -> None:
        self._stream_recorder.read_timeout = value

    @property
    def disconnection_timeout(self) -> int:
        return self._stream_recorder.disconnection_timeout

    @disconnection_timeout.setter
    def disconnection_timeout(self, value: int) -> None:
        self._stream_recorder.disconnection_timeout = value

    @property
    def danmu_uname(self) -> bool:
        return self._danmaku_dumper.danmu_uname

    @danmu_uname.setter
    def danmu_uname(self, value: bool) -> None:
        self._danmaku_dumper.danmu_uname = value

    @property
    def record_gift_send(self) -> bool:
        return self._danmaku_dumper.record_gift_send

    @record_gift_send.setter
    def record_gift_send(self, value: bool) -> None:
        self._danmaku_dumper.record_gift_send = value

    @property
    def record_free_gifts(self) -> bool:
        return self._danmaku_dumper.record_free_gifts

    @record_free_gifts.setter
    def record_free_gifts(self, value: bool) -> None:
        self._danmaku_dumper.record_free_gifts = value

    @property
    def record_guard_buy(self) -> bool:
        return self._danmaku_dumper.record_guard_buy

    @record_guard_buy.setter
    def record_guard_buy(self, value: bool) -> None:
        self._danmaku_dumper.record_guard_buy = value

    @property
    def record_super_chat(self) -> bool:
        return self._danmaku_dumper.record_super_chat

    @record_super_chat.setter
    def record_super_chat(self, value: bool) -> None:
        self._danmaku_dumper.record_super_chat = value

    @property
    def elapsed(self) -> float:
        return self._stream_recorder.elapsed

    @property
    def data_count(self) -> int:
        return self._stream_recorder.data_count

    @property
    def data_rate(self) -> float:
        return self._stream_recorder.data_rate

    @property
    def danmu_count(self) -> int:
        return self._danmaku_dumper.danmu_count

    @property
    def danmu_rate(self) -> float:
        return self._danmaku_dumper.danmu_rate

    @property
    def out_dir(self) -> str:
        return self._stream_recorder.out_dir

    @out_dir.setter
    def out_dir(self, value: str) -> None:
        self._stream_recorder.out_dir = value

    @property
    def path_template(self) -> str:
        return self._stream_recorder.path_template

    @path_template.setter
    def path_template(self, value: str) -> None:
        self._stream_recorder.path_template = value

    @property
    def filesize_limit(self) -> int:
        return self._stream_recorder.filesize_limit

    @filesize_limit.setter
    def filesize_limit(self, value: int) -> None:
        self._stream_recorder.filesize_limit = value

    @property
    def duration_limit(self) -> int:
        return self._stream_recorder.duration_limit

    @duration_limit.setter
    def duration_limit(self, value: int) -> None:
        self._stream_recorder.duration_limit = value

    async def _do_start(self) -> None:
        self._live_monitor.add_listener(self)
        self._danmaku_dumper.add_listener(self)
        self._raw_danmaku_dumper.add_listener(self)
        self._stream_recorder.add_listener(self)
        logger.debug('Started recorder')

        self._print_live_info()
        if self._live.is_living():
            await self._start_recording(stream_available=True)
        else:
            self._print_waiting_message()

    async def _do_stop(self) -> None:
        await self._stop_recording()
        self._live_monitor.remove_listener(self)
        self._danmaku_dumper.remove_listener(self)
        self._raw_danmaku_dumper.remove_listener(self)
        self._stream_recorder.remove_listener(self)
        logger.debug('Stopped recorder')

    def get_recording_files(self) -> Iterator[str]:
        if self._stream_recorder.recording_path is not None:
            yield self._stream_recorder.recording_path
        if self._danmaku_dumper.dumping_path is not None:
            yield self._danmaku_dumper.dumping_path

    def get_video_files(self) -> Iterator[str]:
        yield from self._stream_recorder.get_files()

    def get_danmaku_files(self) -> Iterator[str]:
        yield from self._danmaku_dumper.get_files()

    def can_cut_stream(self) -> bool:
        return self._stream_recorder.can_cut_stream()

    def cut_stream(self) -> bool:
        return self._stream_recorder.cut_stream()

    async def on_live_began(self, live: Live) -> None:
        logger.info('The live has began')
        self._print_live_info()
        await self._start_recording()

    async def on_live_ended(self, live: Live) -> None:
        logger.info('The live has ended')
        await self._stop_recording()
        self._print_waiting_message()

    async def on_live_stream_available(self, live: Live) -> None:
        logger.debug('The live stream becomes available')
        await self._stream_recorder.start()

    async def on_live_stream_reset(self, live: Live) -> None:
        logger.warning('The live stream has been reset')
        if not self._recording:
            await self._start_recording(stream_available=True)

    async def on_room_changed(self, room_info: RoomInfo) -> None:
        self._print_changed_room_info(room_info)
        self._stream_recorder.update_progress_bar_info()

    async def on_video_file_created(
        self, path: str, record_start_time: int
    ) -> None:
        await self._emit('video_file_created', self, path)

    async def on_video_file_completed(self, path: str) -> None:
        await self._emit('video_file_completed', self, path)
        if self.save_cover:
            await self._save_cover_image(path)

    async def on_danmaku_file_created(self, path: str) -> None:
        await self._emit('danmaku_file_created', self, path)

    async def on_danmaku_file_completed(self, path: str) -> None:
        await self._emit('danmaku_file_completed', self, path)

    async def on_raw_danmaku_file_created(self, path: str) -> None:
        await self._emit('raw_danmaku_file_created', self, path)

    async def on_raw_danmaku_file_completed(self, path: str) -> None:
        await self._emit('raw_danmaku_file_completed', self, path)

    async def on_stream_recording_stopped(self) -> None:
        logger.debug('Stream recording stopped')
        await self._stop_recording()

    async def _start_recording(self, stream_available: bool = False) -> None:
        if self._recording:
            return
        self._recording = True

        if self.save_raw_danmaku:
            self._raw_danmaku_dumper.enable()
            self._raw_danmaku_receiver.start()
        self._danmaku_dumper.enable()
        self._danmaku_receiver.start()

        await self._prepare()
        if stream_available:
            await self._stream_recorder.start()

        logger.info('Started recording')
        await self._emit('recording_started', self)

    async def _stop_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False

        await self._stream_recorder.stop()
        if self.save_raw_danmaku:
            self._raw_danmaku_dumper.disable()
            self._raw_danmaku_receiver.stop()
        self._danmaku_dumper.disable()
        self._danmaku_receiver.stop()

        if self._stopped:
            logger.info('Recording Cancelled')
            await self._emit('recording_cancelled', self)
        else:
            logger.info('Recording Finished')
            await self._emit('recording_finished', self)

    async def _prepare(self) -> None:
        live_start_time = self._live.room_info.live_start_time
        self._danmaku_dumper.set_live_start_time(live_start_time)
        self._danmaku_dumper.clear_files()
        self._stream_recorder.clear_files()

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(3))
    @aio_task_with_room_id
    async def _save_cover_image(self, video_path: str) -> None:
        await self._live.update_info()
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            try:
                url = self._live.room_info.cover
                async with session.get(url) as response:
                    ext = url.rsplit('.', 1)[-1]
                    path = cover_path(video_path, ext)
                    async with aiofiles.open(path, 'wb') as file:
                        await file.write(await response.read())
            except Exception as e:
                logger.error(f'Failed to save cover image: {repr(e)}')
                raise
            else:
                logger.info(f'Saved cover image: {path}')

    def _print_waiting_message(self) -> None:
        logger.info('Waiting... until the live starts')

    def _print_live_info(self) -> None:
        room_info = self._live.room_info
        user_info = self._live.user_info

        if room_info.live_start_time > 0:
            live_start_time = str(
                datetime.fromtimestamp(room_info.live_start_time)
            )
        else:
            live_start_time = 'NULL'

        msg = f"""
================================== User Info ==================================
user name        : {user_info.name}
gender           : {user_info.gender}
sign             : {user_info.sign}
uid              : {user_info.uid}
level            : {user_info.level}
---------------------------------- Room Info ----------------------------------
title            : {room_info.title}
cover            : {room_info.cover}
online           : {humanize.intcomma(room_info.online)}
live status      : {room_info.live_status.name}
live start time  : {live_start_time}
room id          : {room_info.room_id}
short room id    : {room_info.short_room_id or 'NULL'}
area id          : {room_info.area_id}
area name        : {room_info.area_name}
parent area id   : {room_info.parent_area_id}
parent area name : {room_info.parent_area_name}
tags             : {room_info.tags}
description      :
{room_info.description}
===============================================================================
"""
        logger.info(msg)

    def _print_changed_room_info(self, room_info: RoomInfo) -> None:
        msg = f"""
================================= Room Change =================================
title            : {room_info.title}
area id          ：{room_info.area_id}
area name        : {room_info.area_name}
parent area id   : {room_info.parent_area_id}
parent area name : {room_info.parent_area_name}
===============================================================================
"""
        logger.info(msg)
