import errno
import os

from fastapi import APIRouter, Body

from blrec.bili.helpers import get_nav

from ...application import Application
from ..schemas import ResponseMessage

app: Application = None  # type: ignore  # bypass flake8 F821

router = APIRouter(prefix='/api/v1/validation', tags=['validation'])


@router.post('/dir', response_model=ResponseMessage)
async def validate_dir(path: str = Body(..., embed=True)) -> ResponseMessage:
    """Check if the path is a directory and grants the read, write permissions"""
    if not os.path.isdir(path):
        return ResponseMessage(code=errno.ENOTDIR, message='not a directory')
    elif not os.access(path, os.F_OK | os.R_OK | os.W_OK):
        return ResponseMessage(code=errno.EACCES, message='no permissions')
    else:
        return ResponseMessage(code=0, message='ok')


@router.post('/cookie', response_model=ResponseMessage)
async def validate_cookie(cookie: str = Body(..., embed=True)) -> ResponseMessage:
    """Check if the cookie is valid"""
    json_res = await get_nav(cookie)
    return ResponseMessage(
        code=json_res['code'], message=json_res['message'], data=json_res['data']
    )
