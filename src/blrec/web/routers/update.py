import asyncio

from fastapi import APIRouter
from loguru import logger

from ... import __prog__
from ...application import Application
from ...update.helpers import get_latest_version_string

app: Application = None  # type: ignore  # bypass flake8 F821

router = APIRouter(prefix='/api/v1/update', tags=['update'])


@router.get('/version/latest')
async def get_latest_version() -> str:
    try:
        return await get_latest_version_string(__prog__) or ''
    except asyncio.TimeoutError:
        logger.warning('Timeout error occurred while getting the latest version string')
        return ''
