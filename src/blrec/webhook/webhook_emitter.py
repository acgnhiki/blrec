import logging
import asyncio
from typing import Any, Dict, List

import aiohttp
from tenacity import (
    AsyncRetrying,
    wait_exponential,
    stop_after_delay,
)

from .models import WebHook
from ..utils.mixins import SwitchableMixin
from ..exception import ExceptionCenter, format_exception
from ..event import EventCenter, Error, ErrorData
from ..event.typing import Event
from .. import __prog__, __version__


__all__ = 'WebHookEmitter',


logger = logging.getLogger(__name__)


class WebHookEmitter(SwitchableMixin):
    def __init__(
        self, webhooks: List[WebHook] = []
    ) -> None:
        super().__init__()
        self.webhooks = webhooks
        self.headers = {
            'User-Agent': f'{__prog__}/{__version__}'
        }

    def _do_enable(self) -> None:
        events = EventCenter.get_instance().events
        self._event_subscription = events.subscribe(self._on_event)
        exceptions = ExceptionCenter.get_instance().exceptions
        self._exc_subscription = exceptions.subscribe(self._on_exception)

    def _do_disable(self) -> None:
        self._event_subscription.dispose()
        self._exc_subscription.dispose()

    def _on_event(self, event: Event) -> None:
        for webhook in self.webhooks:
            if isinstance(event, webhook.event_types):
                self._send_event(webhook.url, event)

    def _on_exception(self, exc: BaseException) -> None:
        for webhook in self.webhooks:
            if webhook.receive_exception:
                self._send_exception(webhook.url, exc)

    def _send_event(self, url: str, event: Event) -> None:
        self._send_request(url, event.asdict())

    def _send_exception(self, url: str, exc: BaseException) -> None:
        data = ErrorData(
            name=type(exc).__name__,
            detail=format_exception(exc),
        )
        payload = Error.from_data(data).asdict()
        self._send_request(url, payload)

    def _send_request(self, url: str, payload: Dict[str, Any]) -> None:
        asyncio.create_task(self._send_request_async(url, payload))

    async def _send_request_async(
        self, url: str, payload: Dict[str, Any]
    ) -> None:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_delay(180),
                wait=wait_exponential(max=15),
            ):
                with attempt:
                    await self._post(url, payload)
        except Exception as e:
            logger.warning('Failed to send a request to {}: {}'.format(
                url, repr(e)
            ))

    async def _post(self, url: str, payload: Dict[str, Any]) -> None:
        async with aiohttp.ClientSession(
            headers=self.headers,
            raise_for_status=True,
        ) as session:
            async with session.post(url, json=payload):
                pass
