from __future__ import annotations
import os
from enum import Enum
from typing import Optional

import attr

from ..bili.models import RoomInfo, UserInfo
from ..bili.typing import QualityNumber
from ..postprocess import DeleteStrategy
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
    # RecorderSettings
    quality_number: QualityNumber
    read_timeout: int
    buffer_size: int
    # PostprocessingOptions
    remux_to_mp4: bool
    delete_source: DeleteStrategy


@attr.s(auto_attribs=True, slots=True, frozen=True)
class TaskData:
    user_info: UserInfo
    room_info: RoomInfo
    task_status: TaskStatus


@attr.s(auto_attribs=True, slots=True, frozen=True)
class FileDetail:
    exists: bool
    path: str
    size: int

    @classmethod
    def from_path(cls, path: str) -> FileDetail:
        try:
            return cls(True, path, os.path.getsize(path))
        except FileNotFoundError:
            return cls(False, path, 0)
