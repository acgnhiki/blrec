
import signal
from typing import Any, Dict

import attr
from fastapi import APIRouter, status

from ..schemas import ResponseMessage
from ...application import Application


app: Application = None  # type: ignore  # bypass flake8 F821

router = APIRouter(
    prefix='/api/v1/app',
    tags=['application'],
)


@router.get(
    '/status',
)
async def get_app_status() -> Dict[str, Any]:
    return attr.asdict(app.status)


@router.get(
    '/info',
)
async def get_app_info() -> Dict[str, Any]:
    return attr.asdict(app.info)


@router.post(
    '/restart',
    response_model=ResponseMessage,
)
async def restart_app() -> ResponseMessage:
    await app.restart()
    return ResponseMessage(message='Application has been restarted')


@router.post(
    '/exit',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def exit_app() -> None:
    signal.raise_signal(signal.SIGINT)
