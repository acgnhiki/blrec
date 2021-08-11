import logging
import asyncio
from abc import ABC, abstractmethod

from tenacity import (
    AsyncRetrying,
    wait_exponential,
    stop_after_delay,
    retry_if_exception,
)

from .providers import (
    EmailService,
    MessagingProvider,
    Serverchan,
    Pushplus,
)
from .message import (
    make_live_info_content,
    make_disk_usage_content,
    make_exception_content,
)
from ..utils.mixins import SwitchableMixin
from ..exception import ExceptionCenter
from ..event import (
    EventCenter,
    LiveBeganEvent,
    LiveEndedEvent,
    SpaceNoEnoughEvent,
)
from ..event.typing import Event


__all__ = (
    'Notifier',
    'MessageNotifier',
    'EmailNotifier',
    'ServerchanNotifier',
    'PushplusNotifier'
)


logger = logging.getLogger(__name__)


class Notifier(SwitchableMixin, ABC):
    def __init__(
        self,
        *,
        notify_began: bool = False,
        notify_ended: bool = False,
        notify_space: bool = False,
        notify_error: bool = False,
    ) -> None:
        super().__init__()
        self.notify_began = notify_began
        self.notify_ended = notify_ended
        self.notify_space = notify_space
        self.notify_error = notify_error

    def _do_enable(self) -> None:
        events = EventCenter.get_instance().events
        self._event_subscription = events.subscribe(self._on_event)
        exceptions = ExceptionCenter.get_instance().exceptions
        self._exc_subscription = exceptions.subscribe(self._on_exception)

    def _do_disable(self) -> None:
        self._event_subscription.dispose()
        self._exc_subscription.dispose()

    def _on_event(self, event: Event) -> None:
        if isinstance(event, LiveBeganEvent):
            if self._should_notify_live_began(event):
                self._notify_live_began(event)
        elif isinstance(event, LiveEndedEvent):
            if self._should_notify_live_ended(event):
                self._notify_live_ended(event)
        elif isinstance(event, SpaceNoEnoughEvent):
            if self._should_notify_space_no_enough(event):
                self._notify_space_no_enough(event)
        else:
            pass

    def _on_exception(self, exc: BaseException) -> None:
        if self._should_notify_exception(exc):
            self._notify_exception(exc)

    def _should_notify_live_began(self, event: LiveBeganEvent) -> bool:
        return self.notify_began

    def _should_notify_live_ended(self, event: LiveEndedEvent) -> bool:
        return self.notify_ended

    def _should_notify_space_no_enough(
        self, event: SpaceNoEnoughEvent
    ) -> bool:
        return self.notify_space

    def _should_notify_exception(self, exc: BaseException) -> bool:
        return self.notify_error

    @abstractmethod
    def _notify_live_began(self, event: LiveBeganEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def _notify_live_ended(self, event: LiveEndedEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def _notify_space_no_enough(self, event: SpaceNoEnoughEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def _notify_exception(self, exc: BaseException) -> None:
        raise NotImplementedError


class MessageNotifier(Notifier, ABC):
    provider: MessagingProvider

    def _notify_live_began(self, event: LiveBeganEvent) -> None:
        title = f'{event.data.user_info.name} 开播啦'
        content = make_live_info_content(
            event.data.user_info, event.data.room_info
        )
        self._send_message(title, content)

    def _notify_live_ended(self, event: LiveEndedEvent) -> None:
        title = f'{event.data.user_info.name} 下播了'
        content = make_live_info_content(
            event.data.user_info, event.data.room_info
        )
        self._send_message(title, content)

    def _notify_space_no_enough(self, event: SpaceNoEnoughEvent) -> None:
        title = '空间不足！'
        content = make_disk_usage_content(event.data)
        self._send_message(title, content)

    def _notify_exception(self, exc: BaseException) -> None:
        title = '出错了~'
        content = make_exception_content(exc)
        self._send_message(title, content)

    def _send_message(self, title: str, content: str) -> None:
        asyncio.create_task(self._send_message_async(title, content))

    async def _send_message_async(self, title: str, content: str) -> None:
        try:
            async for attempt in AsyncRetrying(
                reraise=True,
                stop=stop_after_delay(300),
                wait=wait_exponential(multiplier=0.1, max=10),
                retry=retry_if_exception(
                    lambda e: not isinstance(e, ValueError)
                ),
            ):
                with attempt:
                    await self.provider.send_message(title, content)
        except Exception as e:
            logger.warning('Failed to send a message via {}: {}'.format(
                self.provider.__class__.__name__, repr(e)
            ))


class EmailNotifier(MessageNotifier):
    provider = EmailService.get_instance()

    def _do_enable(self) -> None:
        super()._do_enable()
        logger.debug('Enabled Email notifier')

    def _do_disable(self) -> None:
        super()._do_disable()
        logger.debug('Disabled Email notifier')


class ServerchanNotifier(MessageNotifier):
    provider = Serverchan.get_instance()

    def _do_enable(self) -> None:
        super()._do_enable()
        logger.debug('Enabled Serverchan notifier')

    def _do_disable(self) -> None:
        super()._do_disable()
        logger.debug('Disabled Serverchan notifier')


class PushplusNotifier(MessageNotifier):
    provider = Pushplus.get_instance()

    def _do_enable(self) -> None:
        super()._do_enable()
        logger.debug('Enabled Pushplus notifier')

    def _do_disable(self) -> None:
        super()._do_disable()
        logger.debug('Disabled Pushplus notifier')
