from typing import Optional

from fastapi import APIRouter, Depends

from ..responses import not_found_responses
from ..dependencies import settings_include_set, settings_exclude_set
from ...setting import (
    SettingsIn,
    SettingsOut,
    TaskOptions,
)
from ...setting.typing import KeySetOfSettings
from ...application import Application


app: Application = None  # type: ignore  # bypass flake8 F821

router = APIRouter(
    prefix='/api/v1/settings',
    tags=['settings'],
)


@router.get(
    '',
    response_model=SettingsOut,
    response_model_exclude_unset=True,
)
async def get_settings(
    include: Optional[KeySetOfSettings] = Depends(settings_include_set),
    exclude: Optional[KeySetOfSettings] = Depends(settings_exclude_set),
) -> SettingsOut:
    return app.get_settings(include, exclude)


@router.patch(
    '',
    response_model=SettingsOut,
    response_model_exclude_unset=True,
)
async def change_settings(settings: SettingsIn) -> SettingsOut:
    """Change settings of the application

    Change network request headers will cause
    **all** the Danmaku client be **reconnected**!
    """
    return await app.change_settings(settings)


@router.get(
    '/tasks/{room_id}',
    response_model=TaskOptions,
    response_model_exclude_unset=True,
    responses={**not_found_responses},
)
async def get_task_options(room_id: int) -> TaskOptions:
    return app.get_task_options(room_id)


@router.patch(
    '/tasks/{room_id}',
    response_model=TaskOptions,
    responses={**not_found_responses},
)
async def change_task_options(
    room_id: int, options: TaskOptions
) -> TaskOptions:
    """Change task-specific options

    Task-specific options will shadow the corresponding global settings.
    Explicitly set options to **null** will remove the value shadowing.

    Change network request headers will cause
    the Danmaku client be **reconnected**!
    """
    return await app.change_task_options(room_id, options)
