from typing import Any, Dict, List

import attr
from fastapi import (
    APIRouter,
    status,
    Body,
    Depends,
    BackgroundTasks,
)

from ..dependencies import task_data_filter, TaskDataFilter
from ..schemas import ResponseMessage
from ..responses import (
    not_found_responses,
    forbidden_responses,
    confict_responses,
    accepted_responses,
    created_responses,
)
from ...exception import NotFoundError
from ...application import Application


app: Application = None  # type: ignore  # bypass flake8 F821

router = APIRouter(
    prefix='/api/v1/tasks',
    tags=['tasks'],
)


@router.get('/data')
async def get_all_task_data(
    filter: TaskDataFilter = Depends(task_data_filter)
) -> List[Dict[str, Any]]:
    return [attr.asdict(d) for d in filter(app.get_all_task_data())]


@router.get(
    '/{room_id}/data',
    responses={**not_found_responses},
)
async def get_task_data(room_id: int) -> Dict[str, Any]:
    return attr.asdict(app.get_task_data(room_id))


@router.get(
    '/{room_id}/param',
    responses={**not_found_responses},
)
async def get_task_param(room_id: int) -> Dict[str, Any]:
    return attr.asdict(app.get_task_param(room_id))


@router.get(
    '/{room_id}/files',
    responses={**not_found_responses},
)
async def get_task_file_details(room_id: int) -> List[Dict[str, Any]]:
    return [attr.asdict(d) for d in app.get_task_file_details(room_id)]


@router.post(
    '/info',
    response_model=ResponseMessage,
    responses={**not_found_responses},
)
async def update_all_task_infos() -> ResponseMessage:
    await app.update_all_task_infos()
    return ResponseMessage(message='All task infos have been updated')


@router.post(
    '/{room_id}/info',
    response_model=ResponseMessage,
    responses={**not_found_responses},
)
async def update_task_info(room_id: int) -> ResponseMessage:
    await app.update_task_info(room_id)
    return ResponseMessage(message='The task info has been updated')


@router.post(
    '/start',
    response_model=ResponseMessage,
    responses={**not_found_responses},
)
async def start_all_tasks() -> ResponseMessage:
    await app.start_all_tasks()
    return ResponseMessage(message='All tasks have been started')


@router.post(
    '/{room_id}/start',
    response_model=ResponseMessage,
    responses={**not_found_responses},
)
async def start_task(room_id: int) -> ResponseMessage:
    await app.start_task(room_id)
    return ResponseMessage(message='The task has been started')


@router.post(
    '/stop',
    response_model=ResponseMessage,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**accepted_responses},
)
async def stop_all_tasks(
    background_tasks: BackgroundTasks,
    force: bool = Body(False),
    background: bool = Body(False),
) -> ResponseMessage:
    if background:
        background_tasks.add_task(app.stop_all_tasks, force)
        return ResponseMessage(message='Stopping all tasks on the background')

    await app.stop_all_tasks(force)
    return ResponseMessage(message='All tasks have been stopped')


@router.post(
    '/{room_id}/stop',
    response_model=ResponseMessage,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**not_found_responses, **accepted_responses},
)
async def stop_task(
    background_tasks: BackgroundTasks,
    room_id: int,
    force: bool = Body(False),
    background: bool = Body(False),
) -> ResponseMessage:
    if not app.has_task(room_id):
        raise NotFoundError(f'No task for the room {room_id}')

    if background:
        background_tasks.add_task(app.stop_task, room_id, force)
        return ResponseMessage(message='Stopping the task on the background')

    await app.stop_task(room_id, force)
    return ResponseMessage(message='The task has been stopped')


@router.post(
    '/recorder/enable',
    response_model=ResponseMessage,
)
async def enable_all_task_recorders() -> ResponseMessage:
    await app.enable_all_task_recorders()
    return ResponseMessage(message='All task recorders have been enabled')


@router.post(
    '/{room_id}/recorder/enable',
    response_model=ResponseMessage,
    responses={**not_found_responses},
)
async def enable_task_recorder(room_id: int) -> ResponseMessage:
    await app.enable_task_recorder(room_id)
    return ResponseMessage(message='The task recorder has been enabled')


@router.post(
    '/recorder/disable',
    response_model=ResponseMessage,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**accepted_responses},
)
async def disable_all_task_recorders(
    background_tasks: BackgroundTasks,
    force: bool = Body(False),
    background: bool = Body(False),
) -> ResponseMessage:
    if background:
        background_tasks.add_task(app.disable_all_task_recorders, force)
        return ResponseMessage(
            message='Disabling all task recorders on the background'
        )

    await app.disable_all_task_recorders(force)
    return ResponseMessage(message='All task recorders have been disabled')


@router.post(
    '/{room_id}/recorder/disable',
    response_model=ResponseMessage,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**not_found_responses, **accepted_responses},
)
async def disable_task_recorder(
    background_tasks: BackgroundTasks,
    room_id: int,
    force: bool = Body(False),
    background: bool = Body(False),
) -> ResponseMessage:
    if not app.has_task(room_id):
        raise NotFoundError(f'No task for the room {room_id}')

    if background:
        background_tasks.add_task(app.disable_task_recorder, room_id, force)
        return ResponseMessage(
            message='Disabling the task recorder on the background'
        )

    await app.disable_task_recorder(room_id, force)
    return ResponseMessage(message='The task recorder has been disabled')


@router.post(
    '/{room_id}',
    response_model=ResponseMessage,
    status_code=status.HTTP_201_CREATED,
    responses={
        **created_responses, **confict_responses, **forbidden_responses
    },
)
async def add_task(room_id: int) -> ResponseMessage:
    """Add a task for a room.

    the room_id argument can be both the real room id or the short room id.

    only use the real room id for task management.
    the short room id should be considered as a shorthand
    only for adding tasks conveniently.
    """
    real_room_id = await app.add_task(room_id)
    return ResponseMessage(
        message='Added Task Successfully',
        data={'room_id': real_room_id},
    )


@router.delete(
    '',
    response_model=ResponseMessage,
)
async def remove_all_tasks() -> ResponseMessage:
    await app.remove_all_tasks()
    return ResponseMessage(message='All tasks have been removed')


@router.delete(
    '/{room_id}',
    response_model=ResponseMessage,
    responses={**not_found_responses},
)
async def remove_task(room_id: int) -> ResponseMessage:
    await app.remove_task(room_id)
    return ResponseMessage(message='The task has been removed')
