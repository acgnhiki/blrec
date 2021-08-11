from __future__ import annotations
import asyncio
from typing import Dict, Iterator, TYPE_CHECKING

from blrec.setting.models import OutputSettings

from .task import RecordTask
from .models import TaskData, TaskParam, FileDetail
from ..exception import NotFoundError
if TYPE_CHECKING:
    from ..setting import SettingsManager
from ..setting import (
    HeaderSettings,
    DanmakuSettings,
    RecorderSettings,
    PostprocessingSettings,
    TaskSettings,
)


__all__ = 'RecordTaskManager',


class RecordTaskManager:
    def __init__(self, settings_manager: SettingsManager) -> None:
        self._settings_manager = settings_manager
        self._tasks: Dict[int, RecordTask] = {}
        import threading
        self._lock = threading.Lock()

    async def load_all_tasks(self) -> None:
        settings_list = self._settings_manager.get_settings({'tasks'}).tasks
        assert settings_list is not None

        for settings in settings_list:
            await self.add_task(settings)

    async def destroy_all_tasks(self) -> None:
        if not self._tasks:
            return
        await asyncio.wait([t.destroy() for t in self._tasks.values()])
        self._tasks.clear()

    def has_task(self, room_id: int) -> bool:
        return room_id in self._tasks

    async def add_task(self, settings: TaskSettings) -> None:
        task = RecordTask(settings.room_id)
        self._tasks[settings.room_id] = task

        await self._settings_manager.apply_task_header_settings(
            settings.room_id, settings.header, update_session=False
        )
        await task.setup()

        self._settings_manager.apply_task_output_settings(
            settings.room_id, settings.output
        )
        self._settings_manager.apply_task_danmaku_settings(
            settings.room_id, settings.danmaku
        )
        self._settings_manager.apply_task_recorder_settings(
            settings.room_id, settings.recorder
        )
        self._settings_manager.apply_task_postprocessing_settings(
            settings.room_id, settings.postprocessing
        )

        if settings.enable_monitor:
            await task.enable_monitor()
        if settings.enable_recorder:
            await task.enable_recorder()

    async def remove_task(self, room_id: int) -> None:
        task = self._get_task(room_id)
        await task.disable_recorder(force=True)
        await task.disable_monitor()
        await task.destroy()
        del self._tasks[room_id]

    async def remove_all_tasks(self) -> None:
        coros = [self.remove_task(i) for i in self._tasks]
        if coros:
            await asyncio.wait(coros)

    async def start_task(self, room_id: int) -> None:
        task = self._get_task(room_id)
        await task.update_info()
        await task.enable_monitor()
        await task.enable_recorder()

    async def stop_task(self, room_id: int, force: bool = False) -> None:
        task = self._get_task(room_id)
        await task.disable_recorder(force)
        await task.disable_monitor()

    async def start_all_tasks(self) -> None:
        await self.update_all_task_infos()
        await self.enable_all_task_monitors()
        await self.enable_all_task_recorders()

    async def stop_all_tasks(self, force: bool = False) -> None:
        await self.disable_all_task_recorders(force)
        await self.disable_all_task_monitors()

    async def enable_task_monitor(self, room_id: int) -> None:
        task = self._get_task(room_id)
        await task.enable_monitor()

    async def disable_task_monitor(self, room_id: int) -> None:
        task = self._get_task(room_id)
        await task.disable_monitor()

    async def enable_all_task_monitors(self) -> None:
        coros = [t.enable_monitor() for t in self._tasks.values()]
        if coros:
            await asyncio.wait(coros)

    async def disable_all_task_monitors(self) -> None:
        coros = [t.disable_monitor() for t in self._tasks.values()]
        if coros:
            await asyncio.wait(coros)

    async def enable_task_recorder(self, room_id: int) -> None:
        task = self._get_task(room_id)
        await task.enable_recorder()

    async def disable_task_recorder(
            self, room_id: int, force: bool = False
    ) -> None:
        task = self._get_task(room_id)
        await task.disable_recorder(force)

    async def enable_all_task_recorders(self) -> None:
        coros = [t.enable_recorder() for t in self._tasks.values()]
        if coros:
            await asyncio.wait(coros)

    async def disable_all_task_recorders(self, force: bool = False) -> None:
        coros = [t.disable_recorder(force) for t in self._tasks.values()]
        if coros:
            await asyncio.wait(coros)

    def get_task_data(self, room_id: int) -> TaskData:
        task = self._get_task(room_id)
        assert task.ready, "the task isn't ready yet, couldn't get task data!"
        return self._make_task_data(task)

    def get_all_task_data(self) -> Iterator[TaskData]:
        for task in filter(lambda t: t.ready, self._tasks.values()):
            yield self._make_task_data(task)

    def get_task_param(self, room_id: int) -> TaskParam:
        task = self._get_task(room_id)
        return self._make_task_param(task)

    def get_task_file_details(self, room_id: int) -> Iterator[FileDetail]:
        task = self._get_task(room_id)
        for path in task.files:
            yield FileDetail.from_path(path)

    async def update_task_info(self, room_id: int) -> None:
        task = self._get_task(room_id)
        await task.update_info()

    async def update_all_task_infos(self) -> None:
        coros = [t.update_info() for t in self._tasks.values()]
        if coros:
            await asyncio.wait(coros)

    async def apply_task_header_settings(
        self,
        room_id: int,
        settings: HeaderSettings,
        *,
        update_session: bool = True,
    ) -> None:
        task = self._get_task(room_id)

        # avoid unnecessary updates that will interrupt connections
        if (
            task.user_agent == settings.user_agent and
            task.cookie == settings.cookie
        ):
            return

        task.user_agent = settings.user_agent
        task.cookie = settings.cookie

        if update_session:
            # update task session to take the effect
            await task.update_session()

    def apply_task_output_settings(
        self, room_id: int, settings: OutputSettings
    ) -> None:
        task = self._get_task(room_id)
        task.out_dir = settings.out_dir
        task.path_template = settings.path_template
        task.filesize_limit = settings.filesize_limit
        task.duration_limit = settings.duration_limit

    def apply_task_danmaku_settings(
        self, room_id: int, settings: DanmakuSettings
    ) -> None:
        task = self._get_task(room_id)
        task.danmu_uname = settings.danmu_uname

    def apply_task_recorder_settings(
        self, room_id: int, settings: RecorderSettings
    ) -> None:
        task = self._get_task(room_id)
        task.quality_number = settings.quality_number
        task.read_timeout = settings.read_timeout
        task.buffer_size = settings.buffer_size

    def apply_task_postprocessing_settings(
        self, room_id: int, settings: PostprocessingSettings
    ) -> None:
        task = self._get_task(room_id)
        task.remux_to_mp4 = settings.remux_to_mp4
        task.delete_source = settings.delete_source

    def _get_task(self, room_id: int) -> RecordTask:
        try:
            return self._tasks[room_id]
        except KeyError:
            raise NotFoundError(f'no task for the room {room_id}')

    def _make_task_param(self, task: RecordTask) -> TaskParam:
        return TaskParam(
            out_dir=task.out_dir,
            path_template=task.path_template,
            filesize_limit=task.filesize_limit,
            duration_limit=task.duration_limit,
            user_agent=task.user_agent,
            cookie=task.cookie,
            danmu_uname=task.danmu_uname,
            quality_number=task.quality_number,
            read_timeout=task.read_timeout,
            buffer_size=task.buffer_size,
            remux_to_mp4=task.remux_to_mp4,
            delete_source=task.delete_source,
        )

    def _make_task_data(self, task: RecordTask) -> TaskData:
        return TaskData(
            user_info=task.user_info,
            room_info=task.room_info,
            task_status=task.status,
        )
