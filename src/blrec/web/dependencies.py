from functools import partial
from typing import Callable, Iterable, Iterator, List, Optional, cast

from fastapi import Query

from blrec.setting import KeyOfSettings, KeySetOfSettings

from .schemas import DataSelection, AliasKeyOfSettings
from ..bili.models import LiveStatus
from ..task import RunningStatus, TaskData
from ..utils.string import snake_case


TaskDataFilter = Callable[[Iterable[TaskData]], Iterator[TaskData]]


def task_data_filter(
    select: DataSelection = Query('all'),
) -> TaskDataFilter:
    if select == DataSelection.ALL:
        def func(data: TaskData) -> bool:
            return True
    # live status
    elif select == DataSelection.PREPARING:
        def func(data: TaskData) -> bool:
            return data.room_info.live_status == LiveStatus.PREPARING
    elif select == DataSelection.LIVING:
        def func(data: TaskData) -> bool:
            return data.room_info.live_status == LiveStatus.LIVE
    elif select == DataSelection.ROUNDING:
        def func(data: TaskData) -> bool:
            return data.room_info.live_status == LiveStatus.ROUND
    # task status
    elif select == DataSelection.MONITOR_ENABLED:
        def func(data: TaskData) -> bool:
            return data.task_status.monitor_enabled
    elif select == DataSelection.MONITOR_DISABLED:
        def func(data: TaskData) -> bool:
            return not data.task_status.monitor_enabled
    elif select == DataSelection.RECORDER_ENABLED:
        def func(data: TaskData) -> bool:
            return data.task_status.recorder_enabled
    elif select == DataSelection.RECORDER_DISABLED:
        def func(data: TaskData) -> bool:
            return not data.task_status.recorder_enabled
    # task running status
    elif select == DataSelection.STOPPED:
        def func(data: TaskData) -> bool:
            return data.task_status.running_status == RunningStatus.STOPPED
    elif select == DataSelection.WAITTING:
        def func(data: TaskData) -> bool:
            return data.task_status.running_status == RunningStatus.WAITING
    elif select == DataSelection.RECORDING:
        def func(data: TaskData) -> bool:
            return data.task_status.running_status == RunningStatus.RECORDING
    elif select == DataSelection.REMUXING:
        def func(data: TaskData) -> bool:
            return data.task_status.running_status == RunningStatus.REMUXING

    return partial(filter, func)  # type: ignore


def settings_include_set(
    include: Optional[List[AliasKeyOfSettings]] = Query(None),
) -> Optional[KeySetOfSettings]:
    return frozenset(map(key_of_settings, include)) if include else None


def settings_exclude_set(
    exclude: Optional[List[AliasKeyOfSettings]] = Query(None),
) -> Optional[KeySetOfSettings]:
    return frozenset(map(key_of_settings, exclude)) if exclude else None


def key_of_settings(key: AliasKeyOfSettings) -> KeyOfSettings:
    return cast(KeyOfSettings, snake_case(key))
