import http
import re

from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class RouteRedirectMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app
        self._pattern = re.compile(r'^/(tasks|settings|about)($|/.*$)')

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self._app(scope, receive, send)
            return

        path = scope.get('path', '')
        if self._pattern.match(path):
            status_code = http.HTTPStatus.MOVED_PERMANENTLY.value
            response = RedirectResponse('/', status_code=status_code)
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)
