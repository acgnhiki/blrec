from __future__ import annotations
import os
import asyncio
from typing import Optional, TYPE_CHECKING, cast

from .helpers import update_settings, shadow_settings
from .models import (
    OutputOptions,
    Settings,
    SettingsIn,
    SettingsOut,

    HeaderOptions,
    DanmakuOptions,
    RecorderOptions,
    PostprocessingOptions,

    TaskOptions,
    TaskSettings,
    NotifierSettings,
    NotificationSettings,
)
from .typing import KeySetOfSettings
from ..webhook import WebHook
from ..notification import Notifier, EmailService, Serverchan, Pushplus
from ..logging import configure_logger
from ..exception import NotFoundError
if TYPE_CHECKING:
    from ..application import Application


class SettingsManager:
    def __init__(self, app: Application, settings: Settings) -> None:
        self._app = app
        self._settings = settings

    def get_settings(
        self,
        include: Optional[KeySetOfSettings] = None,
        exclude: Optional[KeySetOfSettings] = None,
    ) -> SettingsOut:
        return SettingsOut(
            **self._settings.dict(include=include, exclude=exclude)
        )

    async def change_settings(self, settings: SettingsIn) -> SettingsOut:
        changed = False

        for name in settings.__fields_set__:
            src_sub_settings = getattr(settings, name)
            dst_sub_settings = getattr(self._settings, name)

            if src_sub_settings == dst_sub_settings:
                continue

            if isinstance(src_sub_settings, list):
                assert isinstance(dst_sub_settings, list)
                setattr(self._settings, name, src_sub_settings)
            else:
                update_settings(src_sub_settings, dst_sub_settings)
            changed = True

            func = getattr(self, f'apply_{name}_settings')
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()

        if changed:
            await self.dump_settings()

        return self.get_settings(
            cast(KeySetOfSettings, settings.__fields_set__)
        )

    def get_task_options(self, room_id: int) -> TaskOptions:
        if (settings := self.find_task_settings(room_id)):
            return TaskOptions.from_settings(settings)
        raise NotFoundError(f'task settings of room {room_id} not found')

    async def change_task_options(
        self,
        room_id: int,
        options: TaskOptions,
    ) -> TaskOptions:
        settings = self.find_task_settings(room_id)
        assert settings is not None

        changed = False

        for name in options.__fields_set__:
            src_opts = getattr(options, name)
            dst_opts = getattr(settings, name)

            if src_opts == dst_opts:
                continue

            update_settings(src_opts, dst_opts)
            changed = True

            func = getattr(self, f'apply_task_{name}_settings')
            if asyncio.iscoroutinefunction(func):
                await func(room_id, dst_opts)
            else:
                func(room_id, dst_opts)

        if changed:
            await self.dump_settings()

        return TaskOptions.from_settings(settings)

    async def dump_settings(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._settings.dump)

    def has_task_settings(self, room_id: int) -> bool:
        return self.find_task_settings(room_id) is not None

    def find_task_settings(self, room_id: int) -> Optional[TaskSettings]:
        for settings in self._settings.tasks:
            if settings.room_id == room_id:
                return settings
        return None

    async def add_task_settings(self, room_id: int) -> TaskSettings:
        settings = TaskSettings(room_id=room_id)
        self._settings.tasks = [*self._settings.tasks, settings]
        await self.dump_settings()
        return settings.copy(deep=True)

    async def remove_task_settings(self, room_id: int) -> None:
        settings = self.find_task_settings(room_id)
        if settings is None:
            raise NotFoundError(f"The room {room_id} is not existed")
        self._settings.tasks.remove(settings)
        await self.dump_settings()

    async def remove_all_task_settings(self) -> None:
        self._settings.tasks.clear()
        await self.dump_settings()

    async def mark_task_enabled(self, room_id: int) -> None:
        settings = self.find_task_settings(room_id)
        assert settings is not None
        settings.enable_monitor = True
        settings.enable_recorder = True
        await self.dump_settings()

    async def mark_task_disabled(self, room_id: int) -> None:
        settings = self.find_task_settings(room_id)
        assert settings is not None
        settings.enable_monitor = False
        settings.enable_recorder = False
        await self.dump_settings()

    async def mark_all_tasks_enabled(self) -> None:
        for settings in self._settings.tasks:
            settings.enable_monitor = True
            settings.enable_recorder = True
        await self.dump_settings()

    async def mark_all_tasks_disabled(self) -> None:
        for settings in self._settings.tasks:
            settings.enable_monitor = False
            settings.enable_recorder = False
        await self.dump_settings()

    async def mark_task_recorder_enabled(self, room_id: int) -> None:
        settings = self.find_task_settings(room_id)
        assert settings is not None
        settings.enable_recorder = True
        await self.dump_settings()

    async def mark_task_recorder_disabled(self, room_id: int) -> None:
        settings = self.find_task_settings(room_id)
        assert settings is not None
        settings.enable_recorder = False
        await self.dump_settings()

    async def mark_all_task_recorders_enabled(self) -> None:
        for settings in self._settings.tasks:
            settings.enable_recorder = True
        await self.dump_settings()

    async def mark_all_task_recorders_disabled(self) -> None:
        for settings in self._settings.tasks:
            settings.enable_recorder = False
        await self.dump_settings()

    async def apply_task_header_settings(
        self,
        room_id: int,
        options: HeaderOptions,
        *,
        update_session: bool = True,
    ) -> None:
        final_settings = self._settings.header.copy()
        shadow_settings(options, final_settings)
        await self._app._task_manager.apply_task_header_settings(
            room_id, final_settings, update_session=update_session
        )

    def apply_task_danmaku_settings(
        self,
        room_id: int,
        options: DanmakuOptions,
    ) -> None:
        final_settings = self._settings.danmaku.copy()
        shadow_settings(options, final_settings)
        self._app._task_manager.apply_task_danmaku_settings(
            room_id, final_settings
        )

    def apply_task_recorder_settings(
        self,
        room_id: int,
        options: RecorderOptions,
    ) -> None:
        final_settings = self._settings.recorder.copy()
        shadow_settings(options, final_settings)
        self._app._task_manager.apply_task_recorder_settings(
            room_id, final_settings
        )

    def apply_task_output_settings(
        self,
        room_id: int,
        options: OutputOptions,
    ) -> None:
        final_settings = self._settings.output.copy()
        shadow_settings(options, final_settings)
        self._app._task_manager.apply_task_output_settings(
            room_id, final_settings
        )

    def apply_task_postprocessing_settings(
        self,
        room_id: int,
        options: PostprocessingOptions,
    ) -> None:
        final_settings = self._settings.postprocessing.copy()
        shadow_settings(options, final_settings)
        self._app._task_manager.apply_task_postprocessing_settings(
            room_id, final_settings
        )

    async def apply_output_settings(self) -> None:
        for settings in self._settings.tasks:
            self.apply_task_output_settings(settings.room_id, settings.output)

        out_dir = self._settings.output.out_dir
        self._app._space_monitor.path = out_dir
        self._app._space_reclaimer.path = out_dir

        prev_out_dir = self._app._out_dir
        self._app._out_dir = out_dir

        if not os.path.samefile(out_dir, prev_out_dir):
            self.apply_logging_settings()

    def apply_logging_settings(self) -> None:
        configure_logger(
            self._app._out_dir,
            console_log_level=self._settings.logging.console_log_level,
            max_bytes=self._settings.logging.max_bytes,
            backup_count=self._settings.logging.backup_count,
        )

    async def apply_header_settings(self) -> None:
        for settings in self._settings.tasks:
            await self.apply_task_header_settings(
                settings.room_id, settings.header
            )

    def apply_danmaku_settings(self) -> None:
        for settings in self._settings.tasks:
            self.apply_task_danmaku_settings(
                settings.room_id, settings.danmaku
            )

    def apply_recorder_settings(self) -> None:
        for settings in self._settings.tasks:
            self.apply_task_recorder_settings(
                settings.room_id, settings.recorder
            )

    def apply_postprocessing_settings(self) -> None:
        for settings in self._settings.tasks:
            self.apply_task_postprocessing_settings(
                settings.room_id, settings.postprocessing
            )

    def apply_space_settings(self) -> None:
        self.apply_space_monitor_settings()
        self.apply_space_reclaimer_settings()

    def apply_space_monitor_settings(self) -> None:
        settings = self._settings.space
        self._app._space_monitor.check_interval = settings.check_interval
        self._app._space_monitor.space_threshold = settings.space_threshold

    def apply_space_reclaimer_settings(self) -> None:
        settings = self._settings.space
        self._app._space_reclaimer.recycle_records = settings.recycle_records

    def apply_email_notification_settings(self) -> None:
        notifier = self._app._email_notifier
        settings = self._settings.email_notification
        self._apply_email_settings(notifier.provider)
        self._apply_notifier_settings(notifier, settings)
        self._apply_notification_settings(notifier, settings)

    def apply_serverchan_notification_settings(self) -> None:
        notifier = self._app._serverchan_notifier
        settings = self._settings.serverchan_notification
        self._apply_serverchan_settings(notifier.provider)
        self._apply_notifier_settings(notifier, settings)
        self._apply_notification_settings(notifier, settings)

    def apply_pushplus_notification_settings(self) -> None:
        notifier = self._app._pushplus_notifier
        settings = self._settings.pushplus_notification
        self._apply_pushplus_settings(notifier.provider)
        self._apply_notifier_settings(notifier, settings)
        self._apply_notification_settings(notifier, settings)

    def apply_webhooks_settings(self) -> None:
        webhooks = [WebHook.from_settings(s) for s in self._settings.webhooks]
        self._app._webhook_emitter.webhooks = webhooks

    def _apply_email_settings(self, email_service: EmailService) -> None:
        email_service.src_addr = self._settings.email_notification.src_addr
        email_service.dst_addr = self._settings.email_notification.dst_addr
        email_service.auth_code = self._settings.email_notification.auth_code
        email_service.smtp_host = self._settings.email_notification.smtp_host
        email_service.smtp_port = self._settings.email_notification.smtp_port

    def _apply_serverchan_settings(self, serverchan: Serverchan) -> None:
        serverchan.sendkey = self._settings.serverchan_notification.sendkey

    def _apply_pushplus_settings(self, pushplus: Pushplus) -> None:
        pushplus.token = self._settings.pushplus_notification.token
        pushplus.topic = self._settings.pushplus_notification.topic

    def _apply_notifier_settings(
        self, notifier: Notifier, settings: NotifierSettings
    ) -> None:
        if settings.enabled:
            notifier.enable()
        else:
            notifier.disable()

    def _apply_notification_settings(
        self, notifier: Notifier, settings: NotificationSettings
    ) -> None:
        notifier.notify_began = settings.notify_began
        notifier.notify_ended = settings.notify_ended
        notifier.notify_error = settings.notify_error
        notifier.notify_space = settings.notify_space
