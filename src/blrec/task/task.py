import logging
import os
from pathlib import Path
from typing import Iterator, Optional

from ..bili.danmaku_client import DanmakuClient
from ..bili.live import Live
from ..bili.live_monitor import LiveMonitor
from ..bili.models import RoomInfo, UserInfo
from ..bili.typing import QualityNumber, StreamFormat
from ..core import Recorder
from ..core.cover_downloader import CoverSaveStrategy
from ..event.event_submitters import (
    LiveEventSubmitter,
    PostprocessorEventSubmitter,
    RecorderEventSubmitter,
)
from ..flv.metadata_injection import InjectingProgress
from ..flv.operators import MetaData, StreamProfile
from ..logging.room_id import aio_task_with_room_id
from ..postprocess import DeleteStrategy, Postprocessor, PostprocessorStatus
from ..postprocess.remux import RemuxingProgress
from .models import (
    DanmakuFileDetail,
    DanmukuFileStatus,
    RunningStatus,
    TaskStatus,
    VideoFileDetail,
    VideoFileStatus,
)

__all__ = ('RecordTask',)


logger = logging.getLogger(__name__)


class RecordTask:
    def __init__(
        self,
        room_id: int,
        *,
        out_dir: str = '',
        path_template: str = '',
        cookie: str = '',
        user_agent: str = '',
        remux_to_mp4: bool = False,
        inject_extra_metadata: bool = True,
        delete_source: DeleteStrategy = DeleteStrategy.AUTO,
    ) -> None:
        super().__init__()

        self._live = Live(room_id, user_agent, cookie)

        self._room_id = room_id
        self._out_dir = out_dir
        self._path_template = path_template
        self._cookie = cookie
        self._user_agent = user_agent
        self._remux_to_mp4 = remux_to_mp4
        self._inject_extra_metadata = inject_extra_metadata
        self._delete_source = delete_source

        self._ready = False
        self._monitor_enabled: bool = False
        self._recorder_enabled: bool = False

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def room_info(self) -> RoomInfo:
        return self._live.room_info

    @property
    def user_info(self) -> UserInfo:
        return self._live.user_info

    @property
    def running_status(self) -> RunningStatus:
        if not self._monitor_enabled and not self._recorder_enabled:
            return RunningStatus.STOPPED
        elif self._recorder.recording:
            return RunningStatus.RECORDING
        elif self._postprocessor.status == PostprocessorStatus.REMUXING:
            return RunningStatus.REMUXING
        elif self._postprocessor.status == PostprocessorStatus.INJECTING:
            return RunningStatus.INJECTING
        else:
            return RunningStatus.WAITING

    @property
    def monitor_enabled(self) -> bool:
        return self._monitor_enabled

    @property
    def recorder_enabled(self) -> bool:
        return self._recorder_enabled

    @property
    def status(self) -> TaskStatus:
        return TaskStatus(
            monitor_enabled=self.monitor_enabled,
            recorder_enabled=self.recorder_enabled,
            running_status=self.running_status,
            stream_url=self._recorder.stream_url,
            stream_host=self._recorder.stream_host,
            dl_total=self._recorder.dl_total,
            dl_rate=self._recorder.dl_rate,
            rec_elapsed=self._recorder.rec_elapsed,
            rec_total=self._recorder.rec_total,
            rec_rate=self._recorder.rec_rate,
            danmu_total=self._recorder.danmu_total,
            danmu_rate=self._recorder.danmu_rate,
            real_stream_format=self._recorder.real_stream_format,
            real_quality_number=self._recorder.real_quality_number,
            recording_path=self.recording_path,
            postprocessor_status=self._postprocessor.status,
            postprocessing_path=self._postprocessor.postprocessing_path,
            postprocessing_progress=(self._postprocessor.postprocessing_progress),
        )

    @property
    def video_file_details(self) -> Iterator[VideoFileDetail]:
        recording_paths = set(self._recorder.get_recording_files())
        completed_paths = set(self._postprocessor.get_completed_files())

        for path in self._recorder.get_video_files():
            try:
                size = os.path.getsize(path)
                exists = True
            except FileNotFoundError:
                mp4_path = str(Path(path).with_suffix('.mp4'))
                try:
                    size = os.path.getsize(mp4_path)
                    exists = True
                    path = mp4_path
                except FileNotFoundError:
                    size = 0
                    exists = False

            if not exists:
                status = VideoFileStatus.MISSING
            elif path in completed_paths:
                status = VideoFileStatus.COMPLETED
            elif path in recording_paths:
                status = VideoFileStatus.RECORDING
            elif path == self._postprocessor.postprocessing_path:
                progress = self._postprocessor.postprocessing_progress
                if isinstance(progress, RemuxingProgress):
                    status = VideoFileStatus.REMUXING
                elif isinstance(progress, InjectingProgress):
                    status = VideoFileStatus.INJECTING
                else:
                    if self._postprocessor.remux_to_mp4:
                        status = VideoFileStatus.REMUXING
                    else:
                        status = VideoFileStatus.INJECTING
            else:
                # disabling recorder by force or stoping task by force
                status = VideoFileStatus.BROKEN

            yield VideoFileDetail(path=path, size=size, status=status)

    @property
    def danmaku_file_details(self) -> Iterator[DanmakuFileDetail]:
        recording_paths = set(self._recorder.get_recording_files())
        completed_paths = set(self._postprocessor.get_completed_files())

        for path in self._recorder.get_danmaku_files():
            try:
                size = os.path.getsize(path)
                exists = True
            except FileNotFoundError:
                size = 0
                exists = False

            if not exists:
                status = DanmukuFileStatus.MISSING
            elif path in completed_paths:
                status = DanmukuFileStatus.COMPLETED
            elif path in recording_paths:
                status = DanmukuFileStatus.RECORDING
            else:
                # disabling recorder by force or stoping task by force
                status = DanmukuFileStatus.BROKEN

            yield DanmakuFileDetail(path=path, size=size, status=status)

    @property
    def user_agent(self) -> str:
        return self._live.user_agent

    @user_agent.setter
    def user_agent(self, value: str) -> None:
        self._live.user_agent = value

    @property
    def cookie(self) -> str:
        return self._live.cookie

    @cookie.setter
    def cookie(self, value: str) -> None:
        self._live.cookie = value

    @property
    def danmu_uname(self) -> bool:
        return self._recorder.danmu_uname

    @danmu_uname.setter
    def danmu_uname(self, value: bool) -> None:
        self._recorder.danmu_uname = value

    @property
    def record_gift_send(self) -> bool:
        return self._recorder.record_gift_send

    @record_gift_send.setter
    def record_gift_send(self, value: bool) -> None:
        self._recorder.record_gift_send = value

    @property
    def record_free_gifts(self) -> bool:
        return self._recorder.record_free_gifts

    @record_free_gifts.setter
    def record_free_gifts(self, value: bool) -> None:
        self._recorder.record_free_gifts = value

    @property
    def record_guard_buy(self) -> bool:
        return self._recorder.record_guard_buy

    @record_guard_buy.setter
    def record_guard_buy(self, value: bool) -> None:
        self._recorder.record_guard_buy = value

    @property
    def record_super_chat(self) -> bool:
        return self._recorder.record_super_chat

    @record_super_chat.setter
    def record_super_chat(self, value: bool) -> None:
        self._recorder.record_super_chat = value

    @property
    def save_cover(self) -> bool:
        return self._recorder.save_cover

    @save_cover.setter
    def save_cover(self, value: bool) -> None:
        self._recorder.save_cover = value

    @property
    def cover_save_strategy(self) -> CoverSaveStrategy:
        return self._recorder.cover_save_strategy

    @cover_save_strategy.setter
    def cover_save_strategy(self, value: CoverSaveStrategy) -> None:
        self._recorder.cover_save_strategy = value

    @property
    def save_raw_danmaku(self) -> bool:
        return self._recorder.save_raw_danmaku

    @save_raw_danmaku.setter
    def save_raw_danmaku(self, value: bool) -> None:
        self._recorder.save_raw_danmaku = value

    @property
    def stream_format(self) -> StreamFormat:
        return self._recorder.stream_format

    @stream_format.setter
    def stream_format(self, value: StreamFormat) -> None:
        self._recorder.stream_format = value

    @property
    def quality_number(self) -> QualityNumber:
        return self._recorder.quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._recorder.quality_number = value

    @property
    def fmp4_stream_timeout(self) -> int:
        return self._recorder.fmp4_stream_timeout

    @fmp4_stream_timeout.setter
    def fmp4_stream_timeout(self, value: int) -> None:
        self._recorder.fmp4_stream_timeout = value

    @property
    def real_stream_format(self) -> Optional[StreamFormat]:
        return self._recorder.real_stream_format

    @property
    def real_quality_number(self) -> Optional[QualityNumber]:
        return self._recorder.real_quality_number

    @property
    def buffer_size(self) -> int:
        return self._recorder.buffer_size

    @buffer_size.setter
    def buffer_size(self, value: int) -> None:
        self._recorder.buffer_size = value

    @property
    def read_timeout(self) -> int:
        return self._recorder.read_timeout

    @read_timeout.setter
    def read_timeout(self, value: int) -> None:
        self._recorder.read_timeout = value

    @property
    def disconnection_timeout(self) -> int:
        return self._recorder.disconnection_timeout

    @disconnection_timeout.setter
    def disconnection_timeout(self, value: int) -> None:
        self._recorder.disconnection_timeout = value

    @property
    def out_dir(self) -> str:
        return self._recorder.out_dir

    @out_dir.setter
    def out_dir(self, value: str) -> None:
        self._recorder.out_dir = value

    @property
    def path_template(self) -> str:
        return self._recorder.path_template

    @path_template.setter
    def path_template(self, value: str) -> None:
        self._recorder.path_template = value

    @property
    def filesize_limit(self) -> int:
        return self._recorder.filesize_limit

    @filesize_limit.setter
    def filesize_limit(self, value: int) -> None:
        self._recorder.filesize_limit = value

    @property
    def duration_limit(self) -> int:
        return self._recorder.duration_limit

    @duration_limit.setter
    def duration_limit(self, value: int) -> None:
        self._recorder.duration_limit = value

    @property
    def recording_path(self) -> Optional[str]:
        return self._recorder.recording_path

    @property
    def metadata(self) -> Optional[MetaData]:
        return self._recorder.metadata

    @property
    def stream_profile(self) -> StreamProfile:
        return self._recorder.stream_profile

    @property
    def remux_to_mp4(self) -> bool:
        return self._postprocessor.remux_to_mp4

    @remux_to_mp4.setter
    def remux_to_mp4(self, value: bool) -> None:
        self._postprocessor.remux_to_mp4 = value

    @property
    def inject_extra_metadata(self) -> bool:
        return self._postprocessor.inject_extra_metadata

    @inject_extra_metadata.setter
    def inject_extra_metadata(self, value: bool) -> None:
        self._postprocessor.inject_extra_metadata = value

    @property
    def delete_source(self) -> DeleteStrategy:
        return self._postprocessor.delete_source

    @delete_source.setter
    def delete_source(self, value: DeleteStrategy) -> None:
        self._postprocessor.delete_source = value

    def can_cut_stream(self) -> bool:
        return self._recorder.can_cut_stream()

    def cut_stream(self) -> bool:
        return self._recorder.cut_stream()

    @aio_task_with_room_id
    async def setup(self) -> None:
        await self._live.init()
        await self._setup()
        self._ready = True

    @aio_task_with_room_id
    async def destroy(self) -> None:
        await self._destroy()
        await self._live.deinit()
        self._ready = False

    @aio_task_with_room_id
    async def enable_monitor(self) -> None:
        if self._monitor_enabled:
            return
        self._monitor_enabled = True

        await self._danmaku_client.start()
        self._live_monitor.enable()

    @aio_task_with_room_id
    async def disable_monitor(self) -> None:
        if not self._monitor_enabled:
            return
        self._monitor_enabled = False

        self._live_monitor.disable()
        await self._danmaku_client.stop()

    @aio_task_with_room_id
    async def enable_recorder(self) -> None:
        if self._recorder_enabled:
            return
        self._recorder_enabled = True

        await self._postprocessor.start()
        await self._recorder.start()

    @aio_task_with_room_id
    async def disable_recorder(self, force: bool = False) -> None:
        if not self._recorder_enabled:
            return
        self._recorder_enabled = False

        if force:
            await self._postprocessor.stop()
            await self._recorder.stop()
        else:
            await self._recorder.stop()
            await self._postprocessor.stop()

    async def update_info(self, raise_exception: bool = False) -> bool:
        return await self._live.update_info(raise_exception=raise_exception)

    @aio_task_with_room_id
    async def update_session(self) -> None:
        if self._monitor_enabled:
            await self._danmaku_client.stop()

        await self._live.deinit()
        await self._live.init()
        self._danmaku_client.session = self._live.session
        self._danmaku_client.appapi = self._live.appapi
        self._danmaku_client.webapi = self._live.webapi

        if self._monitor_enabled:
            await self._danmaku_client.start()

    async def _setup(self) -> None:
        self._setup_danmaku_client()
        self._setup_live_monitor()
        self._setup_live_event_submitter()
        self._setup_recorder()
        self._setup_recorder_event_submitter()
        self._setup_postprocessor()
        self._setup_postprocessor_event_submitter()

    def _setup_danmaku_client(self) -> None:
        self._danmaku_client = DanmakuClient(
            self._live.session, self._live.appapi, self._live.webapi, self._live.room_id
        )

    def _setup_live_monitor(self) -> None:
        self._live_monitor = LiveMonitor(self._danmaku_client, self._live)

    def _setup_live_event_submitter(self) -> None:
        self._live_event_submitter = LiveEventSubmitter(self._live_monitor)

    def _setup_recorder(self) -> None:
        self._recorder = Recorder(
            self._live,
            self._danmaku_client,
            self._live_monitor,
            self._out_dir,
            self._path_template,
        )

    def _setup_recorder_event_submitter(self) -> None:
        self._recorder_event_submitter = RecorderEventSubmitter(self._recorder)

    def _setup_postprocessor(self) -> None:
        self._postprocessor = Postprocessor(
            self._live,
            self._recorder,
            remux_to_mp4=self._remux_to_mp4,
            inject_extra_metadata=self._inject_extra_metadata,
            delete_source=self._delete_source,
        )

    def _setup_postprocessor_event_submitter(self) -> None:
        self._postprocessor_event_submitter = PostprocessorEventSubmitter(
            self._postprocessor
        )

    async def _destroy(self) -> None:
        self._destroy_postprocessor_event_submitter()
        self._destroy_postprocessor()
        self._destroy_recorder_event_submitter()
        self._destroy_recorder()
        self._destroy_live_event_submitter()
        self._destroy_live_monitor()
        self._destroy_danmaku_client()

    def _destroy_danmaku_client(self) -> None:
        del self._danmaku_client

    def _destroy_live_monitor(self) -> None:
        del self._live_monitor

    def _destroy_live_event_submitter(self) -> None:
        del self._live_event_submitter

    def _destroy_recorder(self) -> None:
        del self._recorder

    def _destroy_recorder_event_submitter(self) -> None:
        del self._recorder_event_submitter

    def _destroy_postprocessor(self) -> None:
        del self._postprocessor

    def _destroy_postprocessor_event_submitter(self) -> None:
        del self._postprocessor_event_submitter
