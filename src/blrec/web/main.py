import os
from typing import Optional, Tuple

from brotli_asgi import BrotliMiddleware
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pkg_resources import resource_filename
from pydantic import ValidationError
from starlette.responses import Response

from blrec.exception import ExistsError, ForbiddenError, NotFoundError
from blrec.path.helpers import create_file, file_exists
from blrec.setting import EnvSettings, Settings
from blrec.web.middlewares.base_herf import BaseHrefMiddleware
from blrec.web.middlewares.route_redirect import RouteRedirectMiddleware

from ..application import Application
from . import security
from .routers import application, settings, tasks, update, validation, websockets
from .schemas import ResponseMessage

_env_settings = EnvSettings()
_path = os.path.abspath(os.path.expanduser(_env_settings.settings_file))
if not file_exists(_path):
    create_file(_path)
_env_settings.settings_file = _path

_settings = Settings.load(_env_settings.settings_file)
_settings.update_from_env_settings(_env_settings)

app = Application(_settings)

if _env_settings.api_key is None:
    _dependencies = None
else:
    security.api_key = _env_settings.api_key
    _dependencies = [Depends(security.authenticate)]

api = FastAPI(
    title='Bilibili live streaming recorder web API',
    description='Web API to communicate with the backend application',
    version='v1',
    dependencies=_dependencies,
)

api.add_middleware(BaseHrefMiddleware)
api.add_middleware(BrotliMiddleware)
api.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:4200'],  # angular development
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
api.add_middleware(RouteRedirectMiddleware)


@api.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=dict(ResponseMessage(code=status.HTTP_404_NOT_FOUND, message=str(exc))),
    )


@api.exception_handler(ForbiddenError)
async def forbidden_error_handler(
    request: Request, exc: ForbiddenError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=dict(ResponseMessage(code=status.HTTP_403_FORBIDDEN, message=str(exc))),
    )


@api.exception_handler(ExistsError)
async def exists_error_handler(request: Request, exc: ExistsError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=dict(ResponseMessage(code=status.HTTP_409_CONFLICT, message=str(exc))),
    )


@api.exception_handler(ValidationError)
async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        content=dict(
            ResponseMessage(code=status.HTTP_406_NOT_ACCEPTABLE, message=str(exc))
        ),
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
    def lookup_path(self, path: str) -> Tuple[str, Optional[os.stat_result]]:
        if path == '404.html':
            path = 'index.html'
        return super().lookup_path(path)

    def file_response(self, full_path: str, *args, **kwargs) -> Response:  # type: ignore # noqa
        # ignore MIME types from Windows registry
        # workaround for https://github.com/acgnhiki/blrec/issues/12
        response = super().file_response(full_path, *args, **kwargs)
        if full_path.endswith('.js'):
            js_media_type = 'application/javascript'
            if response.media_type != js_media_type:
                response.media_type = js_media_type
                headers = response.headers
                headers['content-type'] = js_media_type
                response.raw_headers = headers.raw
                del response._headers
        return response


directory = resource_filename(__name__, '../data/webapp')
api.mount('/', WebAppFiles(directory=directory, html=True), name='webapp')
