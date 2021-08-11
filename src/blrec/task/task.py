import logging
from typing import List, Optional


from .models import RunningStatus, TaskStatus
from ..bili.live import Live
from ..bili.models import RoomInfo, UserInfo
from ..bili.danmaku_client import DanmakuClient
from ..bili.live_monitor import LiveMonitor
from ..bili.typing import QualityNumber
from ..core import Recorder
from ..postprocess import Postprocessor, ProcessStatus, DeleteStrategy
from ..event.event_submitters import (
    LiveEventSubmitter, PostprocessorEventSubmitter
)
from ..logging.room_id import aio_task_with_room_id


__all__ = 'RecordTask',


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
        danmu_uname: bool = False,
        buffer_size: Optional[int] = None,
        read_timeout: Optional[int] = None,
        filesize_limit: int = 0,
        duration_limit: int = 0,
        remux_to_mp4: bool = False,
        delete_source: DeleteStrategy = DeleteStrategy.AUTO,
    ) -> None:
        super().__init__()

        self._live = Live(room_id, user_agent, cookie)

        self._room_id = room_id
        self._out_dir = out_dir
        self._path_template = path_template
        self._cookie = cookie
        self._user_agent = user_agent
        self._danmu_uname = danmu_uname
        self._buffer_size = buffer_size
        self._read_timeout = read_timeout
        self._filesize_limit = filesize_limit
        self._duration_limit = duration_limit
        self._remux_to_mp4 = remux_to_mp4
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
        elif self._postprocessor.status == ProcessStatus.REMUXING:
            return RunningStatus.REMUXING
        elif self._postprocessor.status == ProcessStatus.INJECTING:
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
            elapsed=self._recorder.elapsed,
            data_count=self._recorder.data_count,
            data_rate=self._recorder.data_rate,
            danmu_count=self._recorder.danmu_count,
            danmu_rate=self._recorder.danmu_rate,
            real_quality_number=self._recorder.real_quality_number,
            postprocessing_path=self._postprocessor.postprocessing_path,
            postprocessing_progress=(
                self._postprocessor.postprocessing_progress
            ),
        )

    @property
    def files(self) -> List[str]:
        if self.running_status == RunningStatus.STOPPED:
            return []
        if (
            self.running_status == RunningStatus.RECORDING or
            not self._postprocessor.enabled
        ):
            return [
                *self._recorder.get_video_files(),
                *self._recorder.get_danmaku_files(),
            ]
        return [*self._postprocessor.get_final_files()]

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
    def quality_number(self) -> QualityNumber:
        return self._recorder.quality_number

    @quality_number.setter
    def quality_number(self, value: QualityNumber) -> None:
        self._recorder.quality_number = value

    @property
    def real_quality_number(self) -> QualityNumber:
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
    def remux_to_mp4(self) -> bool:
        return self._postprocessor.remux_to_mp4

    @remux_to_mp4.setter
    def remux_to_mp4(self, value: bool) -> None:
        self._postprocessor.remux_to_mp4 = value

    @property
    def delete_source(self) -> DeleteStrategy:
        return self._postprocessor.delete_source

    @delete_source.setter
    def delete_source(self, value: DeleteStrategy) -> None:
        self._postprocessor.delete_source = value

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

        self._postprocessor.enable()
        await self._recorder.start()

    @aio_task_with_room_id
    async def disable_recorder(self, force: bool = False) -> None:
        if not self._recorder_enabled:
            return
        self._recorder_enabled = False

        if force:
            self._postprocessor.disable()
            await self._recorder.stop()
        else:
            await self._recorder.stop()
            await self._postprocessor.wait()
            self._postprocessor.disable()

    async def update_info(self) -> None:
        await self._live.update_info()

    @aio_task_with_room_id
    async def update_session(self) -> None:
        if self._monitor_enabled:
            await self._danmaku_client.stop()

        await self._live.deinit()
        await self._live.init()
        self._danmaku_client.session = self._live.session

        if self._monitor_enabled:
            await self._danmaku_client.start()

    async def _setup(self) -> None:
        self._setup_danmaku_client()
        self._setup_live_monitor()
        self._setup_live_event_submitter()
        self._setup_recorder()
        self._setup_postprocessor()
        self._setup_postprocessor_event_submitter()

    def _setup_danmaku_client(self) -> None:
        self._danmaku_client = DanmakuClient(
            self._live.session, self._live.room_id
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
            buffer_size=self._buffer_size,
            read_timeout=self._read_timeout,
            danmu_uname=self._danmu_uname,
            filesize_limit=self._filesize_limit,
            duration_limit=self._duration_limit,
        )

    def _setup_postprocessor_event_submitter(self) -> None:
        self._postprocessor_event_submitter = \
            PostprocessorEventSubmitter(self._postprocessor)

    def _setup_postprocessor(self) -> None:
        self._postprocessor = Postprocessor(
            self._live,
            self._recorder,
            remux_to_mp4=self._remux_to_mp4,
            delete_source=self._delete_source,
        )

    async def _destroy(self) -> None:
        self._destroy_postprocessor_event_submitter()
        self._destroy_postprocessor()
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

    def _destroy_postprocessor_event_submitter(self) -> None:
        del self._postprocessor_event_submitter

    def _destroy_postprocessor(self) -> None:
        del self._postprocessor
