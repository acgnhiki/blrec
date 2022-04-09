from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import Iterator, Optional, Type

import aiohttp
import aiofiles
import humanize
from tenacity import retry, wait_fixed, stop_after_attempt

from .danmaku_receiver import DanmakuReceiver
from .danmaku_dumper import DanmakuDumper, DanmakuDumperEventListener
from .raw_danmaku_receiver import RawDanmakuReceiver
from .raw_danmaku_dumper import RawDanmakuDumper, RawDanmakuDumperEventListener
from .base_stream_recorder import (
    BaseStreamRecorder, StreamRecorderEventListener
)
from .stream_analyzer import StreamProfile
from .flv_stream_recorder import FLVStreamRecorder
from .hls_stream_recorder import HLSStreamRecorder
from ..event.event_emitter import EventListener, EventEmitter
from ..flv.data_analyser import MetaData
from ..bili.live import Live
from ..bili.models import RoomInfo
from ..bili.danmaku_client import DanmakuClient
from ..bili.live_monitor import LiveMonitor, LiveEventListener
from ..bili.typing import StreamFormat, QualityNumber
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
        stream_format: StreamFormat = 'flv',
        quality_number: QualityNumber = 10000,
        buffer_size: Optional[int] = None,
        read_timeout: Optional[int] = None,
        disconnection_timeout: Optional[int] = None,
        filesize_limit: int = 0,
        duration_limit: int = 0,
        danmu_uname: bool = False,
        record_gift_send: bool = False,
        record_free_gifts: bool = False,
        record_guard_buy: bool = False,
        record_super_chat: bool = False,
        save_cover: bool = False,
        save_raw_danmaku: bool = False,
    ) -> None:
        super().__init__()

        self._live = live
        self._danmaku_client = danmaku_client
        self._live_monitor = live_monitor
        self.save_cover = save_cover
        self.save_raw_danmaku = save_raw_danmaku

        self._recording: bool = False
        self._stream_available: bool = False

        cls: Type[BaseStreamRecorder]
        if stream_format == 'flv':
            cls = FLVStreamRecorder
        else:
            cls = HLSStreamRecorder
        self._stream_recorder = cls(
            self._live,
            out_dir=out_dir,
            path_template=path_template,
            stream_format=stream_format,
            quality_number=quality_number,
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
            self._live,
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
    def stream_format(self) -> StreamFormat:
        return self._stream_recorder.stream_format

    @stream_format.setter
    def stream_format(self, value: StreamFormat) -> None:
        self._stream_recorder.stream_format = value

    @property
    def quality_number(self) -> QualityNumber:
        return self._stream_recorder.quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._stream_recorder.quality_number = value

    @property
    def real_stream_format(self) -> StreamFormat:
        return self._stream_recorder.real_stream_format

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
    def stream_url(self) -> str:
        return self._stream_recorder.stream_url

    @property
    def stream_host(self) -> str:
        return self._stream_recorder.stream_host

    @property
    def dl_total(self) -> int:
        return self._stream_recorder.dl_total

    @property
    def dl_rate(self) -> float:
        return self._stream_recorder.dl_rate

    @property
    def rec_elapsed(self) -> float:
        return self._stream_recorder.rec_elapsed

    @property
    def rec_total(self) -> int:
        return self._stream_recorder.rec_total

    @property
    def rec_rate(self) -> float:
        return self._stream_recorder.rec_rate

    @property
    def danmu_total(self) -> int:
        return self._danmaku_dumper.danmu_total

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

    @property
    def recording_path(self) -> Optional[str]:
        return self._stream_recorder.recording_path

    @property
    def metadata(self) -> Optional[MetaData]:
        return self._stream_recorder.metadata

    @property
    def stream_profile(self) -> StreamProfile:
        return self._stream_recorder.stream_profile

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
        self._stream_available = False
        await self._stop_recording()
        self._print_waiting_message()

    async def on_live_stream_available(self, live: Live) -> None:
        logger.debug('The live stream becomes available')
        self._stream_available = True
        await self._stream_recorder.start()

    async def on_live_stream_reset(self, live: Live) -> None:
        logger.warning('The live stream has been reset')
        if not self._recording:
            await self._start_recording()

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

    async def _do_start(self) -> None:
        self._live_monitor.add_listener(self)
        self._danmaku_dumper.add_listener(self)
        self._raw_danmaku_dumper.add_listener(self)
        self._stream_recorder.add_listener(self)
        logger.debug('Started recorder')

        self._print_live_info()
        if self._live.is_living():
            self._stream_available = True
            await self._start_recording()
        else:
            self._print_waiting_message()

    async def _do_stop(self) -> None:
        await self._stop_recording()
        self._live_monitor.remove_listener(self)
        self._danmaku_dumper.remove_listener(self)
        self._raw_danmaku_dumper.remove_listener(self)
        self._stream_recorder.remove_listener(self)
        logger.debug('Stopped recorder')

    async def _start_recording(self) -> None:
        if self._recording:
            return
        self._change_stream_recorder()
        self._recording = True

        if self.save_raw_danmaku:
            self._raw_danmaku_dumper.enable()
            self._raw_danmaku_receiver.start()
        self._danmaku_dumper.enable()
        self._danmaku_receiver.start()

        await self._prepare()
        if self._stream_available:
            await self._stream_recorder.start()
        else:
            asyncio.create_task(self._guard())

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

    @aio_task_with_room_id
    async def _guard(self, timeout: float = 60) -> None:
        await asyncio.sleep(timeout)
        if not self._recording:
            return
        if self._stream_available:
            return
        logger.debug(
            f'Stream not available in {timeout} seconds, the event maybe lost.'
        )

        await self._live.update_info()
        if self._live.is_living():
            logger.debug('The live is living now')
            self._stream_available = True
            if self._stream_recorder.stopped:
                await self._stream_recorder.start()
        else:
            logger.debug('The live has ended before streaming')
            self._stream_available = False
            if not self._stream_recorder.stopped:
                await self.stop()

    def _change_stream_recorder(self) -> None:
        if self._recording:
            logger.debug('Can not change stream recorder while recording')
            return

        cls: Type[BaseStreamRecorder]
        if self.stream_format == 'flv':
            cls = FLVStreamRecorder
        else:
            cls = HLSStreamRecorder

        if self._stream_recorder.__class__ == cls:
            return

        self._stream_recorder.remove_listener(self)
        self._stream_recorder = cls(
            self._live,
            out_dir=self.out_dir,
            path_template=self.path_template,
            stream_format=self.stream_format,
            quality_number=self.quality_number,
            buffer_size=self.buffer_size,
            read_timeout=self.read_timeout,
            disconnection_timeout=self.disconnection_timeout,
            filesize_limit=self.filesize_limit,
            duration_limit=self.duration_limit,
        )
        self._stream_recorder.add_listener(self)

        self._danmaku_dumper.change_stream_recorder(self._stream_recorder)
        self._raw_danmaku_dumper.change_stream_recorder(self._stream_recorder)

        logger.debug(f'Changed stream recorder to {cls.__name__}')

    @aio_task_with_room_id
    async def _save_cover_image(self, video_path: str) -> None:
        try:
            await self._live.update_info()
            url = self._live.room_info.cover
            ext = url.rsplit('.', 1)[-1]
            path = cover_path(video_path, ext)
            await self._save_file(url, path)
        except Exception as e:
            logger.error(f'Failed to save cover image: {repr(e)}')
        else:
            logger.info(f'Saved cover image: {path}')

    @retry(reraise=True, wait=wait_fixed(1), stop=stop_after_attempt(3))
    async def _save_file(self, url: str, path: str) -> None:
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.get(url) as response:
                async with aiofiles.open(path, 'wb') as file:
                    await file.write(await response.read())

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
