from __future__ import annotations
from enum import Enum
from typing import Optional

import attr

from ..bili.models import RoomInfo, UserInfo
from ..bili.typing import QualityNumber
from ..postprocess import DeleteStrategy, PostprocessorStatus
from ..postprocess.typing import Progress


class RunningStatus(str, Enum):
    STOPPED = 'stopped'
    WAITING = 'waiting'
    RECORDING = 'recording'
    REMUXING = 'remuxing'
    INJECTING = 'injecting'


@attr.s(auto_attribs=True, slots=True, frozen=True)
class TaskStatus:
    monitor_enabled: bool
    recorder_enabled: bool
    running_status: RunningStatus
    elapsed: float  # time elapsed
    data_count: int  # Number of Bytes in total
    data_rate: float  # Number of Bytes per second
    danmu_count: int  # Number of Danmu in total
    danmu_rate: float  # Number of Danmu per minutes
    real_quality_number: QualityNumber
    postprocessor_status: PostprocessorStatus = PostprocessorStatus.WAITING
    postprocessing_path: Optional[str] = None
    postprocessing_progress: Optional[Progress] = None


@attr.s(auto_attribs=True, slots=True, frozen=True)
class TaskParam:
    # OutputSettings
    out_dir: str
    path_template: str
    filesize_limit: int
    duration_limit: int
    # HeaderSettings
    user_agent: str
    cookie: str
    # DanmakuSettings
    danmu_uname: bool
    record_gift_send: bool
    record_free_gifts: bool
    record_guard_buy: bool
    record_super_chat: bool
    save_raw_danmaku: bool
    # RecorderSettings
    quality_number: QualityNumber
    read_timeout: int
    disconnection_timeout: Optional[int]
    buffer_size: int
    save_cover: bool
    # PostprocessingOptions
    remux_to_mp4: bool
    inject_extra_metadata: bool
    delete_source: DeleteStrategy


@attr.s(auto_attribs=True, slots=True, frozen=True)
class TaskData:
    user_info: UserInfo
    room_info: RoomInfo
    task_status: TaskStatus


class VideoFileStatus(str, Enum):
    RECORDING = 'recording'
    REMUXING = 'remuxing'
    INJECTING = 'injecting'
    COMPLETED = 'completed'
    MISSING = 'missing'
    BROKEN = 'broken'


class DanmukuFileStatus(str, Enum):
    RECORDING = 'recording'
    COMPLETED = 'completed'
    MISSING = 'missing'
    BROKEN = 'broken'


@attr.s(auto_attribs=True, slots=True, frozen=True)
class VideoFileDetail:
    path: str
    size: int
    status: VideoFileStatus


@attr.s(auto_attribs=True, slots=True, frozen=True)
class DanmakuFileDetail:
    path: str
    size: int
    status: DanmukuFileStatus
