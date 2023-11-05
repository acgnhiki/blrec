import asyncio
import os
from contextlib import suppress
from typing import Iterator, List, Optional

import attr
import psutil
from loguru import logger

from . import __prog__, __version__
from .bili.helpers import ensure_room_id
from .core.typing import MetaData
from .disk_space import SpaceMonitor, SpaceReclaimer
from .event.event_submitters import SpaceEventSubmitter
from .exception import ExceptionHandler, ExistsError, exception_callback
from .flv.operators import StreamProfile
from .notification import (
    BarkNotifier,
    EmailNotifier,
    PushdeerNotifier,
    PushplusNotifier,
    ServerchanNotifier,
    TelegramNotifier,
)
from .setting import Settings, SettingsIn, SettingsManager, SettingsOut, TaskOptions
from .setting.typing import KeySetOfSettings
from .task import (
    DanmakuFileDetail,
    RecordTaskManager,
    TaskData,
    TaskParam,
    VideoFileDetail,
)
from .webhook import WebHookEmitter


@attr.s(auto_attribs=True, slots=True, frozen=True)
class AppInfo:
    name: str
    version: str
    pid: int
    ppid: int
    create_time: float
    cwd: str
    exe: str
    cmdline: List[str]


@attr.s(auto_attribs=True, slots=True, frozen=True)
class AppStatus:
    cpu_percent: float
    memory_percent: float
    num_threads: int


class Application:
    def __init__(self, settings: Settings) -> None:
        self._out_dir = settings.output.out_dir
        self._settings_manager = SettingsManager(self, settings)
        self._task_manager = RecordTaskManager(self._settings_manager)

    @property
    def info(self) -> AppInfo:
        p = psutil.Process(os.getpid())
        with p.oneshot():
            return AppInfo(
                name=__prog__,
                version=__version__,
                pid=p.pid,
                ppid=p.ppid(),
                create_time=p.create_time(),
                cwd=p.cwd(),
                exe=p.exe(),
                cmdline=p.cmdline(),
            )

    @property
    def status(self) -> AppStatus:
        p = psutil.Process(os.getpid())
        with p.oneshot():
            return AppStatus(
                cpu_percent=p.cpu_percent(),
                memory_percent=p.memory_percent(),
                num_threads=p.num_threads(),
            )

    def run(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()

        await self.launch()
        try:
            self._interrupt_event = asyncio.Event()
            await self._interrupt_event.wait()
        finally:
            await self.exit()

    async def launch(self) -> None:
        self._setup_logger()
        logger.info('Launching Application...')
        self._setup()
        logger.debug(f'Default umask {os.umask(0o000)}')
        logger.info(f'Launched Application v{__version__}')
        self._loading_task = asyncio.create_task(self._task_manager.load_all_tasks())

        def callback(future: asyncio.Future) -> None:  # type: ignore
            del self._loading_task

        self._loading_task.add_done_callback(exception_callback)
        self._loading_task.add_done_callback(callback)

    async def exit(self) -> None:
        logger.info('Exiting Application...')
        await self._exit()
        logger.info('Exited Application')

    async def abort(self) -> None:
        logger.info('Aborting Application...')
        await self._exit(force=True)
        logger.info('Aborted Application')

    async def _exit(self, force: bool = False) -> None:
        if hasattr(self, '_loading_task'):
            self._loading_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._loading_task
        await self._task_manager.stop_all_tasks(force=force)
        await self._task_manager.destroy_all_tasks()
        self._destroy()

    async def restart(self) -> None:
        logger.info('Restarting Application...')
        await self.exit()
        await self.launch()
        logger.info('Restarted Application')

    def has_task(self, room_id: int) -> bool:
        return self._task_manager.has_task(room_id)

    async def add_task(self, room_id: int) -> int:
        room_id = await ensure_room_id(room_id)

        if self._task_manager.has_task(room_id):
            raise ExistsError(f'a task for the room {room_id} is already existed')

        settings = self._settings_manager.find_task_settings(room_id)
        if not settings:
            settings = await self._settings_manager.add_task_settings(room_id)

        await self._task_manager.add_task(settings)

        return room_id

    async def remove_task(self, room_id: int) -> None:
        logger.info(f'Removing task {room_id}...')
        await self._task_manager.remove_task(room_id)
        await self._settings_manager.remove_task_settings(room_id)
        logger.info(f'Successfully removed task {room_id}')

    async def remove_all_tasks(self) -> None:
        logger.info('Removing all tasks...')
        await self._task_manager.remove_all_tasks()
        await self._settings_manager.remove_all_task_settings()
        logger.info('Successfully removed all tasks')

    async def start_task(self, room_id: int) -> None:
        logger.info(f'Starting task {room_id}...')
        await self._task_manager.start_task(room_id)
        await self._settings_manager.mark_task_enabled(room_id)
        logger.info(f'Successfully started task {room_id}')

    async def stop_task(self, room_id: int, force: bool = False) -> None:
        logger.info(f'Stopping task {room_id}...')
        await self._task_manager.stop_task(room_id, force)
        await self._settings_manager.mark_task_disabled(room_id)
        logger.info(f'Successfully stopped task {room_id}')

    async def start_all_tasks(self) -> None:
        logger.info('Starting all tasks...')
        await self._task_manager.start_all_tasks()
        await self._settings_manager.mark_all_tasks_enabled()
        logger.info('Successfully started all tasks')

    async def stop_all_tasks(self, force: bool = False) -> None:
        logger.info('Stopping all tasks...')
        await self._task_manager.stop_all_tasks(force)
        await self._settings_manager.mark_all_tasks_disabled()
        logger.info('Successfully stopped all tasks')

    async def enable_task_monitor(self, room_id: int) -> None:
        logger.info(f'Enabling monitor for task {room_id}...')
        await self._task_manager.enable_task_monitor(room_id)
        await self._settings_manager.mark_task_monitor_enabled(room_id)
        logger.info(f'Successfully enabled monitor for task {room_id}')

    async def disable_task_monitor(self, room_id: int) -> None:
        logger.info(f'Disabling monitor for task {room_id}...')
        await self._task_manager.disable_task_monitor(room_id)
        await self._settings_manager.mark_task_monitor_disabled(room_id)
        logger.info(f'Successfully disabled monitor for task {room_id}')

    async def enable_all_task_monitors(self) -> None:
        logger.info('Enabling monitors for all tasks...')
        await self._task_manager.enable_all_task_monitors()
        await self._settings_manager.mark_all_task_monitors_enabled()
        logger.info('Successfully enabled monitors for all tasks')

    async def disable_all_task_monitors(self) -> None:
        logger.info('Disabling monitors for all tasks...')
        await self._task_manager.disable_all_task_monitors()
        await self._settings_manager.mark_all_task_monitors_disabled()
        logger.info('Successfully disabled monitors for all tasks')

    async def enable_task_recorder(self, room_id: int) -> None:
        logger.info(f'Enabling recorder for task {room_id}...')
        await self._task_manager.enable_task_recorder(room_id)
        await self._settings_manager.mark_task_recorder_enabled(room_id)
        logger.info(f'Successfully enabled recorder for task {room_id}')

    async def disable_task_recorder(self, room_id: int, force: bool = False) -> None:
        logger.info(f'Disabling recorder for task {room_id}...')
        await self._task_manager.disable_task_recorder(room_id, force)
        await self._settings_manager.mark_task_recorder_disabled(room_id)
        logger.info(f'Successfully disabled recorder for task {room_id}')

    async def enable_all_task_recorders(self) -> None:
        logger.info('Enabling recorders for all tasks...')
        await self._task_manager.enable_all_task_recorders()
        await self._settings_manager.mark_all_task_recorders_enabled()
        logger.info('Successfully enabled recorders for all tasks')

    async def disable_all_task_recorders(self, force: bool = False) -> None:
        logger.info('Disabling recorders for all tasks...')
        await self._task_manager.disable_all_task_recorders(force)
        await self._settings_manager.mark_all_task_recorders_disabled()
        logger.info('Successfully disabled recorders for all tasks')

    def get_task_data(self, room_id: int) -> TaskData:
        return self._task_manager.get_task_data(room_id)

    def get_all_task_data(self) -> Iterator[TaskData]:
        yield from self._task_manager.get_all_task_data()

    def get_task_param(self, room_id: int) -> TaskParam:
        return self._task_manager.get_task_param(room_id)

    def get_task_metadata(self, room_id: int) -> Optional[MetaData]:
        return self._task_manager.get_task_metadata(room_id)

    def get_task_stream_profile(self, room_id: int) -> StreamProfile:
        return self._task_manager.get_task_stream_profile(room_id)

    def get_task_video_file_details(self, room_id: int) -> Iterator[VideoFileDetail]:
        yield from self._task_manager.get_task_video_file_details(room_id)

    def get_task_danmaku_file_details(
        self, room_id: int
    ) -> Iterator[DanmakuFileDetail]:
        yield from self._task_manager.get_task_danmaku_file_details(room_id)

    def can_cut_stream(self, room_id: int) -> bool:
        return self._task_manager.can_cut_stream(room_id)

    def cut_stream(self, room_id: int) -> bool:
        return self._task_manager.cut_stream(room_id)

    async def update_task_info(self, room_id: int) -> None:
        logger.info(f'Updating info for task {room_id}...')
        await self._task_manager.update_task_info(room_id)
        logger.info(f'Successfully updated info for task {room_id}')

    async def update_all_task_infos(self) -> None:
        logger.info('Updating info for all tasks...')
        await self._task_manager.update_all_task_infos()
        logger.info('Successfully updated info for all tasks')

    def get_settings(
        self,
        include: Optional[KeySetOfSettings] = None,
        exclude: Optional[KeySetOfSettings] = None,
    ) -> SettingsOut:
        return self._settings_manager.get_settings(include, exclude)

    async def change_settings(self, settings: SettingsIn) -> SettingsOut:
        return await self._settings_manager.change_settings(settings)

    def get_task_options(self, room_id: int) -> TaskOptions:
        return self._settings_manager.get_task_options(room_id)

    async def change_task_options(
        self, room_id: int, options: TaskOptions
    ) -> TaskOptions:
        return await self._settings_manager.change_task_options(room_id, options)

    def _setup(self) -> None:
        self._setup_exception_handler()
        self._setup_space_monitor()
        self._setup_space_event_submitter()
        self._setup_space_reclaimer()
        self._setup_notifiers()
        self._setup_webhooks()

    def _setup_logger(self) -> None:
        self._settings_manager.apply_logging_settings()

    def _setup_exception_handler(self) -> None:
        self._exception_handler = ExceptionHandler()
        self._exception_handler.enable()

    def _setup_space_monitor(self) -> None:
        self._space_monitor = SpaceMonitor(self._out_dir)
        self._settings_manager.apply_space_monitor_settings()
        self._space_monitor.enable()

    def _setup_space_event_submitter(self) -> None:
        self._space_event_submitter = SpaceEventSubmitter(self._space_monitor)

    def _setup_space_reclaimer(self) -> None:
        self._space_reclaimer = SpaceReclaimer(self._space_monitor, self._out_dir)
        self._settings_manager.apply_space_reclaimer_settings()
        self._space_reclaimer.enable()

    def _setup_notifiers(self) -> None:
        self._email_notifier = EmailNotifier()
        self._serverchan_notifier = ServerchanNotifier()
        self._pushdeer_notifier = PushdeerNotifier()
        self._pushplus_notifier = PushplusNotifier()
        self._telegram_notifier = TelegramNotifier()
        self._bark_notifier = BarkNotifier()
        self._settings_manager.apply_email_notification_settings()
        self._settings_manager.apply_serverchan_notification_settings()
        self._settings_manager.apply_pushdeer_notification_settings()
        self._settings_manager.apply_pushplus_notification_settings()
        self._settings_manager.apply_telegram_notification_settings()
        self._settings_manager.apply_bark_notification_settings()

    def _setup_webhooks(self) -> None:
        self._webhook_emitter = WebHookEmitter()
        self._settings_manager.apply_webhooks_settings()
        self._webhook_emitter.enable()

    def _destroy(self) -> None:
        self._destroy_space_reclaimer()
        self._destroy_space_event_submitter()
        self._destroy_space_monitor()
        self._destroy_notifiers()
        self._destroy_webhooks()
        self._destroy_exception_handler()

    def _destroy_space_monitor(self) -> None:
        self._space_monitor.disable()
        del self._space_monitor

    def _destroy_space_event_submitter(self) -> None:
        del self._space_event_submitter

    def _destroy_space_reclaimer(self) -> None:
        self._space_reclaimer.disable()
        del self._space_reclaimer

    def _destroy_notifiers(self) -> None:
        self._email_notifier.disable()
        self._serverchan_notifier.disable()
        self._pushdeer_notifier.disable()
        self._pushplus_notifier.disable()
        self._telegram_notifier.disable()
        self._bark_notifier.disable()
        del self._email_notifier
        del self._serverchan_notifier
        del self._pushdeer_notifier
        del self._pushplus_notifier
        del self._telegram_notifier
        del self._bark_notifier

    def _destroy_webhooks(self) -> None:
        self._webhook_emitter.disable()
        del self._webhook_emitter

    def _destroy_exception_handler(self) -> None:
        self._exception_handler.disable()
        del self._exception_handler
