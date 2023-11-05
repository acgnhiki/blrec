import asyncio
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Final, Optional, Tuple

import attr
import humanize
from liquid import Environment
from liquid.filter import math_filter
from pkg_resources import resource_string
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_delay,
    wait_exponential,
)

from ..event import (
    Error,
    ErrorData,
    EventCenter,
    LiveBeganEvent,
    LiveEndedEvent,
    SpaceNoEnoughEvent,
)
from ..event.typing import Event
from ..exception import ExceptionCenter, format_exception
from ..setting.typing import MessageType
from ..utils.mixins import SwitchableMixin
from .providers import (
    Bark,
    EmailService,
    MessagingProvider,
    Pushdeer,
    Pushplus,
    Serverchan,
    Telegram,
)

__all__ = (
    'Notifier',
    'MessageNotifier',
    'EmailNotifier',
    'ServerchanNotifier',
    'PushdeerNotifier',
    'PushplusNotifier',
    'TelegramNotifier',
    'BarkNotifier',
)


from loguru import logger


class Notifier(SwitchableMixin, ABC):
    def __init__(
        self,
        *,
        notify_began: bool = False,
        notify_ended: bool = False,
        notify_space: bool = False,
        notify_error: bool = False,
        began_message_type: MessageType = 'text',
        began_message_title: str = '',
        began_message_content: str = '',
        ended_message_type: MessageType = 'text',
        ended_message_title: str = '',
        ended_message_content: str = '',
        space_message_type: MessageType = 'text',
        space_message_title: str = '',
        space_message_content: str = '',
        error_message_type: MessageType = 'text',
        error_message_title: str = '',
        error_message_content: str = '',
    ) -> None:
        super().__init__()

        self._liquid_env = Environment()
        self._liquid_env.add_filter('intcomma', math_filter(humanize.intcomma))
        self._liquid_env.add_filter('naturalsize', math_filter(humanize.naturalsize))
        self._liquid_env.add_filter(
            'datetimestring',
            math_filter(lambda n: datetime.fromtimestamp(n).isoformat()),
        )

        self.notify_began = notify_began
        self.notify_ended = notify_ended
        self.notify_space = notify_space
        self.notify_error = notify_error
        self.began_message_type = began_message_type
        self.began_message_title = began_message_title
        self.began_message_content = began_message_content
        self.ended_message_type = ended_message_type
        self.ended_message_title = ended_message_title
        self.ended_message_content = ended_message_content
        self.space_message_type = space_message_type
        self.space_message_title = space_message_title
        self.space_message_content = space_message_content
        self.error_message_type = error_message_type
        self.error_message_title = error_message_title
        self.error_message_content = error_message_content

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
            error = Error.from_data(ErrorData.from_exc(exc))
            self._notify_exception(error)

    def _should_notify_live_began(self, event: LiveBeganEvent) -> bool:
        return self.notify_began

    def _should_notify_live_ended(self, event: LiveEndedEvent) -> bool:
        return self.notify_ended

    def _should_notify_space_no_enough(self, event: SpaceNoEnoughEvent) -> bool:
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
    def _notify_exception(self, event: Error) -> None:
        raise NotImplementedError

    @abstractmethod
    def _make_began_message(self, event: LiveBeganEvent) -> Tuple[str, str]:
        raise NotImplementedError

    @abstractmethod
    def _make_ended_message(self, event: LiveEndedEvent) -> Tuple[str, str]:
        raise NotImplementedError

    @abstractmethod
    def _make_space_message(self, event: SpaceNoEnoughEvent) -> Tuple[str, str]:
        raise NotImplementedError

    @abstractmethod
    def _make_error_message(self, event: Error) -> Tuple[str, str]:
        raise NotImplementedError


BEGAN_MESSAGE_TITLE: Final[str] = '{{ event.data.user_info.name }} 开播啦'
ENDED_MESSAGE_TITLE: Final[str] = '{{ event.data.user_info.name }} 下播了'
SPACE_MESSAGE_TITLE: Final[str] = '空间不足！'
ERROR_MESSAGE_TITLE: Final[str] = '出错了~'


class MessageNotifier(Notifier, ABC):
    provider: MessagingProvider

    def _notify_live_began(self, event: LiveBeganEvent) -> None:
        title, content = self._make_began_message(event)
        self._send_message(title, content, self.began_message_type)

    def _notify_live_ended(self, event: LiveEndedEvent) -> None:
        title, content = self._make_ended_message(event)
        self._send_message(title, content, self.ended_message_type)

    def _notify_space_no_enough(self, event: SpaceNoEnoughEvent) -> None:
        title, content = self._make_space_message(event)
        self._send_message(title, content, self.space_message_type)

    def _notify_exception(self, event: Error) -> None:
        title, content = self._make_error_message(event)
        self._send_message(title, content, self.error_message_type)

    def _make_began_message(self, event: LiveBeganEvent) -> Tuple[str, str]:
        env = os.environ.copy()
        try:
            template = self._liquid_env.from_string(self._get_began_message_title())
            title = template.render(event=attr.asdict(event), env=env)
            template = self._liquid_env.from_string(self._get_began_message_content())
            content = template.render(event=attr.asdict(event), env=env)
        except Exception as e:
            logger.warning(f'Failed to render began message template: {repr(e)}')
            title = f'{event.data.user_info.name} 开播啦'
            content = format_exception(e)
        return title, content

    def _make_ended_message(self, event: LiveEndedEvent) -> Tuple[str, str]:
        env = os.environ.copy()
        try:
            template = self._liquid_env.from_string(self._get_ended_message_title())
            title = template.render(event=attr.asdict(event), env=env)
            template = self._liquid_env.from_string(self._get_ended_message_content())
            content = template.render(event=attr.asdict(event), env=env)
        except Exception as e:
            logger.warning(f'Failed to render ended message template: {repr(e)}')
            title = f'{event.data.user_info.name} 下播了'
            content = format_exception(e)
        return title, content

    def _make_space_message(self, event: SpaceNoEnoughEvent) -> Tuple[str, str]:
        env = os.environ.copy()
        try:
            template = self._liquid_env.from_string(self._get_space_message_title())
            title = template.render(event=attr.asdict(event), env=env)
            template = self._liquid_env.from_string(self._get_space_message_content())
            content = template.render(event=attr.asdict(event), env=env)
        except Exception as e:
            logger.warning(f'Failed to render space message template: {repr(e)}')
            title = '空间不足！'
            content = format_exception(e)
        return title, content

    def _make_error_message(self, event: Error) -> Tuple[str, str]:
        env = os.environ.copy()
        try:
            template = self._liquid_env.from_string(self._get_error_message_title())
            title = template.render(event=attr.asdict(event), env=env)
            template = self._liquid_env.from_string(self._get_error_message_content())
            content = template.render(event=attr.asdict(event), env=env)
        except Exception as e:
            logger.warning(f'Failed to render error message template: {repr(e)}')
            title = '出错了~'
            content = format_exception(e)
        return title, content

    def _send_message(self, title: str, content: str, msg_type: MessageType) -> None:
        asyncio.create_task(self._send_message_async(title, content, msg_type))

    async def _send_message_async(
        self, title: str, content: str, msg_type: MessageType
    ) -> None:
        try:
            async for attempt in AsyncRetrying(
                reraise=True,
                stop=stop_after_delay(300),
                wait=wait_exponential(multiplier=0.1, max=10),
                retry=retry_if_exception(lambda e: not isinstance(e, ValueError)),
            ):
                with attempt:
                    await self.provider.send_message(title, content, msg_type)
        except Exception as e:
            logger.warning(
                'Failed to send a message via {}: {}'.format(
                    self.provider.__class__.__name__, repr(e)
                )
            )

    def _get_began_message_title(self) -> str:
        return self.began_message_title or BEGAN_MESSAGE_TITLE

    def _get_began_message_content(self, msg_type: Optional[MessageType] = None) -> str:
        if self.began_message_content:
            return self.began_message_content
        msg_type = msg_type or self.began_message_type
        if msg_type == 'markdown':
            relpath = '../data/message_templates/markdown/live-began.md'
        elif msg_type == 'html':
            relpath = '../data/message_templates/html/live-began.html'
        else:
            relpath = '../data/message_templates/text/live-began.txt'
        return resource_string(__name__, relpath).decode('utf-8')

    def _get_ended_message_title(self) -> str:
        return self.ended_message_title or ENDED_MESSAGE_TITLE

    def _get_ended_message_content(self, msg_type: Optional[MessageType] = None) -> str:
        if self.ended_message_content:
            return self.ended_message_content
        msg_type = msg_type or self.ended_message_type
        if msg_type == 'markdown':
            relpath = '../data/message_templates/markdown/live-ended.md'
        elif msg_type == 'html':
            relpath = '../data/message_templates/html/live-ended.html'
        else:
            relpath = '../data/message_templates/text/live-ended.txt'
        return resource_string(__name__, relpath).decode('utf-8')

    def _get_space_message_title(self) -> str:
        return self.space_message_title or SPACE_MESSAGE_TITLE

    def _get_space_message_content(self, msg_type: Optional[MessageType] = None) -> str:
        if self.space_message_content:
            return self.space_message_content
        msg_type = msg_type or self.space_message_type
        if msg_type == 'markdown':
            relpath = '../data/message_templates/markdown/space-no-enough.md'
        elif msg_type == 'html':
            relpath = '../data/message_templates/html/space-no-enough.html'
        else:
            relpath = '../data/message_templates/text/space-no-enough.txt'
        return resource_string(__name__, relpath).decode('utf-8')

    def _get_error_message_title(self) -> str:
        return self.error_message_title or ERROR_MESSAGE_TITLE

    def _get_error_message_content(self, msg_type: Optional[MessageType] = None) -> str:
        if self.error_message_content:
            return self.error_message_content
        msg_type = msg_type or self.error_message_type
        if msg_type == 'markdown':
            relpath = '../data/message_templates/markdown/error.md'
        elif msg_type == 'html':
            relpath = '../data/message_templates/html/error.html'
        else:
            relpath = '../data/message_templates/text/error.txt'
        return resource_string(__name__, relpath).decode('utf-8')


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


class PushdeerNotifier(MessageNotifier):
    provider = Pushdeer.get_instance()

    def _do_enable(self) -> None:
        super()._do_enable()
        logger.debug('Enabled Pushdeer notifier')

    def _do_disable(self) -> None:
        super()._do_disable()
        logger.debug('Disabled Pushdeer notifier')


class PushplusNotifier(MessageNotifier):
    provider = Pushplus.get_instance()

    def _do_enable(self) -> None:
        super()._do_enable()
        logger.debug('Enabled Pushplus notifier')

    def _do_disable(self) -> None:
        super()._do_disable()
        logger.debug('Disabled Pushplus notifier')


class TelegramNotifier(MessageNotifier):
    provider = Telegram.get_instance()

    def _do_enable(self) -> None:
        super()._do_enable()
        logger.debug('Enabled Telegram notifier')

    def _do_disable(self) -> None:
        super()._do_disable()
        logger.debug('Disabled Telegram notifier')

    def _get_began_message_content(self, msg_type: Optional[MessageType] = None) -> str:
        return super()._get_began_message_content(msg_type='text')

    def _get_ended_message_content(self, msg_type: Optional[MessageType] = None) -> str:
        return super()._get_ended_message_content(msg_type='text')

    def _get_space_message_content(self, msg_type: Optional[MessageType] = None) -> str:
        return super()._get_space_message_content(msg_type='text')

    def _get_error_message_content(self, msg_type: Optional[MessageType] = None) -> str:
        return super()._get_error_message_content(msg_type='text')


class BarkNotifier(MessageNotifier):
    provider = Bark.get_instance()

    def _do_enable(self) -> None:
        super()._do_enable()
        logger.debug('Enabled Bark notifier')

    def _do_disable(self) -> None:
        super()._do_disable()
        logger.debug('Disabled Bark notifier')
