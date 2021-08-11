import os
import logging
import secrets
from typing import Optional, Tuple

from fastapi import FastAPI, status, Request, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from pkg_resources import resource_filename

from .routers import (
    tasks, settings, application, validation, websockets, update
)
from .schemas import ResponseMessage
from ..setting import EnvSettings, Settings
from ..application import Application
from ..exception import NotFoundError, ExistsError


logger = logging.getLogger(__name__)


_env_settings = EnvSettings()
_settings = Settings.load(_env_settings.settings_file)
_settings.update_from_env_settings(_env_settings)
app = Application(_settings)

if _env_settings.api_key is None:
    _dependencies = None
else:
    async def validate_api_key(
        x_api_key: Optional[str] = Header(None)
    ) -> None:
        assert _env_settings.api_key is not None
        if (
            x_api_key is None or
            not secrets.compare_digest(x_api_key, _env_settings.api_key)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='API key is missing or invalid',
            )

    _dependencies = [Depends(validate_api_key)]

api = FastAPI(
    title='Bilibili live streaming recorder web API',
    description='Web API to communicate with the backend application',
    version='v1',
    dependencies=_dependencies,
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:4200',  # angular development
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@api.exception_handler(NotFoundError)
async def not_found_error_handler(
    request: Request, exc: NotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=dict(ResponseMessage(
            code=status.HTTP_404_NOT_FOUND,
            message=str(exc),
        )),
    )


@api.exception_handler(ExistsError)
async def exists_error_handler(
    request: Request, exc: ExistsError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=dict(ResponseMessage(
            code=status.HTTP_409_CONFLICT,
            message=str(exc),
        )),
    )


@api.exception_handler(ValidationError)
async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        content=dict(ResponseMessage(
            code=status.HTTP_406_NOT_ACCEPTABLE,
            message=str(exc),
        )),
    )


@api.on_event('startup')
async def on_startup() -> None:
    await app.launch()


@api.on_event('shutdown')
async def on_shuntdown() -> None:
    _settings.dump()
    await app.exit()


tasks.app = app
settings.app = app
application.app = app
validation.app = app
websockets.app = app
update.app = app
api.include_router(tasks.router)
api.include_router(settings.router)
api.include_router(application.router)
api.include_router(validation.router)
api.include_router(websockets.router)
api.include_router(update.router)


class WebAppFiles(StaticFiles):
    async def lookup_path(
        self, path: str
    ) -> Tuple[str, Optional[os.stat_result]]:
        if path == '404.html':
            path = 'index.html'
        return await super().lookup_path(path)


directory = resource_filename(__name__, '../data/webapp')
api.mount('/', WebAppFiles(directory=directory, html=True), name='webapp')
