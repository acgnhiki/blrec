import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from websockets.exceptions import ConnectionClosed

from ...application import Application
from ...event import EventCenter
from ...event.typing import Event
from ...exception import ExceptionCenter, format_exception

logging.getLogger('websockets').setLevel(logging.WARNING)

app: Application = None  # type: ignore  # bypass flake8 F821

router = APIRouter(tags=['websockets'])


@router.websocket('/ws/v1/events')
async def receive_events(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.debug('Events websocket accepted')

    future = asyncio.Future()  # type: ignore

    async def send_event(event: Event) -> None:
        try:
            text = json.dumps(event.asdict(), ensure_ascii=False)
            await websocket.send_text(text)
        except (WebSocketDisconnect, ConnectionClosed) as e:
            logger.debug(f'Events websocket closed: {repr(e)}')
            subscription.dispose()
            future.set_result(None)
        except Exception as e:
            logger.error(f'Error occurred on events websocket: {repr(e)}')
            subscription.dispose()
            future.set_exception(e)

    def on_event(event: Event) -> None:
        asyncio.create_task(send_event(event))

    subscription = EventCenter.get_instance().events.subscribe(on_event)

    await future


@router.websocket('/ws/v1/exceptions')
async def receive_exception(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.debug('Exceptions websocket accepted')

    future = asyncio.Future()  # type: ignore

    async def send_exception(exc: BaseException) -> None:
        try:
            await websocket.send_text(format_exception(exc))
        except (WebSocketDisconnect, ConnectionClosed) as e:
            logger.debug(f'Exceptions websocket closed: {repr(e)}')
            subscription.dispose()
            future.set_result(None)
        except Exception as e:
            logger.error(f'Error occurred on exceptions websocket: {repr(e)}')
            subscription.dispose()
            future.set_exception(e)

    def on_exception(exc: BaseException) -> None:
        asyncio.create_task(send_exception(exc))

    subscription = ExceptionCenter.get_instance().exceptions.subscribe(on_exception)

    await future
