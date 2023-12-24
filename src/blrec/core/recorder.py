from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Iterator, Optional

import humanize
from loguru import logger

from blrec.bili.danmaku_client import DanmakuClient
from blrec.bili.live import Live
from blrec.bili.live_monitor import LiveEventListener, LiveMonitor
from blrec.bili.models import RoomInfo
from blrec.bili.typing import QualityNumber, StreamFormat
from blrec.core.typing import MetaData
from blrec.event.event_emitter import EventEmitter, EventListener
from blrec.flv.operators import StreamProfile
from blrec.setting.typing import RecordingMode
from blrec.utils.mixins import AsyncStoppableMixin

from .cover_downloader import (
    CoverDownloader,
    CoverDownloaderEventListener,
    CoverSaveStrategy,
)
from .danmaku_dumper import DanmakuDumper, DanmakuDumperEventListener
from .danmaku_receiver import DanmakuReceiver
from .raw_danmaku_dumper import RawDanmakuDumper, RawDanmakuDumperEventListener
from .raw_danmaku_receiver import RawDanmakuReceiver
from .stream_recorder import StreamRecorder, StreamRecorderEventListener

__all__ = 'RecorderEventListener', 'Recorder'


class RecorderEventListener(EventListener):
    async def on_recording_started(self, recorder: Recorder) -> None:
        ...

    async def on_recording_finished(self, recorder: Recorder) -> None:
        ...

    async def on_recording_cancelled(self, recorder: Recorder) -> None:
        ...

    async def on_video_file_created(self, recorder: Recorder, path: str) -> None:
        ...

    async def on_video_file_completed(self, recorder: Recorder, path: str) -> None:
        ...

    async def on_danmaku_file_created(self, recorder: Recorder, path: str) -> None:
        ...

    async def on_danmaku_file_completed(self, recorder: Recorder, path: str) -> None:
        ...

    async def on_raw_danmaku_file_created(self, recorder: Recorder, path: str) -> None:
        ...

    async def on_raw_danmaku_file_completed(
        self, recorder: Recorder, path: str
    ) -> None:
        ...

    async def on_cover_image_downloaded(self, recorder: Recorder, path: str) -> None:
        ...


class Recorder(
    EventEmitter[RecorderEventListener],
    LiveEventListener,
    AsyncStoppableMixin,
    DanmakuDumperEventListener,
    RawDanmakuDumperEventListener,
    CoverDownloaderEventListener,
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
        recording_mode: RecordingMode = 'standard',
        quality_number: QualityNumber = 10000,
        fmp4_stream_timeout: int = 10,
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
        cover_save_strategy: CoverSaveStrategy = CoverSaveStrategy.DEFAULT,
        save_raw_danmaku: bool = False,
    ) -> None:
        super().__init__()
        self._logger_context = {'room_id': live.room_id}
        self._logger = logger.bind(**self._logger_context)

        self._live = live
        self._danmaku_client = danmaku_client
        self._live_monitor = live_monitor
        self.save_raw_danmaku = save_raw_danmaku

        self._recording: bool = False
        self._stream_available: bool = False

        self._stream_recorder = StreamRecorder(
            live,
            live_monitor,
            out_dir=out_dir,
            path_template=path_template,
            stream_format=stream_format,
            recording_mode=recording_mode,
            quality_number=quality_number,
            fmp4_stream_timeout=fmp4_stream_timeout,
            buffer_size=buffer_size,
            read_timeout=read_timeout,
            disconnection_timeout=disconnection_timeout,
            filesize_limit=filesize_limit,
            duration_limit=duration_limit,
        )

        self._danmaku_receiver = DanmakuReceiver(live, danmaku_client)
        self._danmaku_dumper = DanmakuDumper(
            live,
            self._stream_recorder,
            self._danmaku_receiver,
            danmu_uname=danmu_uname,
            record_gift_send=record_gift_send,
            record_free_gifts=record_free_gifts,
            record_guard_buy=record_guard_buy,
            record_super_chat=record_super_chat,
        )
        self._raw_danmaku_receiver = RawDanmakuReceiver(live, danmaku_client)
        self._raw_danmaku_dumper = RawDanmakuDumper(
            live, self._stream_recorder, self._raw_danmaku_receiver
        )

        self._cover_downloader = CoverDownloader(
            live,
            self._stream_recorder,
            save_cover=save_cover,
            cover_save_strategy=cover_save_strategy,
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
    def recording_mode(self) -> RecordingMode:
        return self._stream_recorder.recording_mode

    @recording_mode.setter
    def recording_mode(self, value: RecordingMode) -> None:
        self._stream_recorder.recording_mode = value

    @property
    def quality_number(self) -> QualityNumber:
        return self._stream_recorder.quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._stream_recorder.quality_number = value

    @property
    def fmp4_stream_timeout(self) -> int:
        return self._stream_recorder.fmp4_stream_timeout

    @fmp4_stream_timeout.setter
    def fmp4_stream_timeout(self, value: int) -> None:
        self._stream_recorder.fmp4_stream_timeout = value

    @property
    def real_stream_format(self) -> Optional[StreamFormat]:
        return self._stream_recorder.real_stream_format

    @property
    def real_quality_number(self) -> Optional[QualityNumber]:
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
    def save_cover(self) -> bool:
        return self._cover_downloader.save_cover

    @save_cover.setter
    def save_cover(self, value: bool) -> None:
        self._cover_downloader.save_cover = value

    @property
    def cover_save_strategy(self) -> CoverSaveStrategy:
        return self._cover_downloader.cover_save_strategy

    @cover_save_strategy.setter
    def cover_save_strategy(self, value: CoverSaveStrategy) -> None:
        self._cover_downloader.cover_save_strategy = value

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
        self._logger.info('The live has began')
        self._print_live_info()
        await self._start_recording()

    async def on_live_ended(self, live: Live) -> None:
        self._logger.info('The live has ended')
        await asyncio.sleep(3)
        self._stream_available = False
        self._stream_recorder.stream_available_time = None
        await self._stop_recording()
        self._print_waiting_message()

    async def on_live_stream_available(self, live: Live) -> None:
        self._logger.debug('The live stream becomes available')
        self._stream_available = True
        self._stream_recorder.stream_available_time = await live.get_timestamp()
        await self._stream_recorder.start()

    async def on_live_stream_reset(self, live: Live) -> None:
        self._logger.warning('The live stream has been reset')
        if not self._recording:
            await self._start_recording()

    async def on_room_changed(self, room_info: RoomInfo) -> None:
        self._print_changed_room_info(room_info)
        self._stream_recorder.update_progress_bar_info()

    async def on_video_file_created(self, path: str, record_start_time: int) -> None:
        await self._emit('video_file_created', self, path)

    async def on_video_file_completed(self, path: str) -> None:
        await self._emit('video_file_completed', self, path)

    async def on_danmaku_file_created(self, path: str) -> None:
        await self._emit('danmaku_file_created', self, path)

    async def on_danmaku_file_completed(self, path: str) -> None:
        await self._emit('danmaku_file_completed', self, path)

    async def on_raw_danmaku_file_created(self, path: str) -> None:
        await self._emit('raw_danmaku_file_created', self, path)

    async def on_raw_danmaku_file_completed(self, path: str) -> None:
        await self._emit('raw_danmaku_file_completed', self, path)

    async def on_cover_image_downloaded(self, path: str) -> None:
        await self._emit('cover_image_downloaded', self, path)

    async def on_stream_recording_completed(self) -> None:
        self._logger.debug('Stream recording completed')
        await self._stop_recording()

    async def _do_start(self) -> None:
        self._live_monitor.add_listener(self)
        self._danmaku_dumper.add_listener(self)
        self._raw_danmaku_dumper.add_listener(self)
        self._cover_downloader.add_listener(self)
        self._logger.debug('Started recorder')

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
        self._cover_downloader.remove_listener(self)
        self._logger.debug('Stopped recorder')

    async def _start_recording(self) -> None:
        if self._recording:
            return
        self._recording = True

        if self.save_raw_danmaku:
            self._raw_danmaku_dumper.enable()
            self._raw_danmaku_receiver.start()
        self._danmaku_dumper.enable()
        self._danmaku_receiver.start()
        self._cover_downloader.enable()
        self._stream_recorder.add_listener(self)

        await self._prepare()
        if self._stream_available:
            await self._stream_recorder.start()

        self._logger.info('Started recording')
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
        self._cover_downloader.disable()
        self._stream_recorder.remove_listener(self)

        if self._stopped:
            self._logger.info('Recording Cancelled')
            await self._emit('recording_cancelled', self)
        else:
            self._logger.info('Recording Finished')
            await self._emit('recording_finished', self)

    async def _prepare(self) -> None:
        live_start_time = self._live.room_info.live_start_time
        self._danmaku_dumper.set_live_start_time(live_start_time)
        self._danmaku_dumper.clear_files()
        self._stream_recorder.clear_files()

    def _print_waiting_message(self) -> None:
        self._logger.info('Waiting... until the live starts')

    def _print_live_info(self) -> None:
        room_info = self._live.room_info
        user_info = self._live.user_info

        if room_info.live_start_time > 0:
            live_start_time = str(datetime.fromtimestamp(room_info.live_start_time))
        else:
            live_start_time = 'NULL'

        msg = f"""
================================== User Info ==================================
user id          : {user_info.uid}
user name        : {user_info.name}
gender           : {user_info.gender}
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
        self._logger.info(msg)

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
        self._logger.info(msg)
