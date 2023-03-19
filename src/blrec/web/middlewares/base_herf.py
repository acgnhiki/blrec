from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BaseHrefMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope['type'] != 'http'
            or scope.get('method', '') != 'GET'
            or scope.get('path', '') != '/'
            or scope.get('root_path', '') == ''
        ):
            await self._app(scope, receive, send)
            return

        initial_message: Message = {}

        async def _send(msg: Message) -> None:
            nonlocal initial_message
            msg_type = msg['type']
            if msg_type == 'http.response.start':
                headers = Headers(raw=msg['headers'])
                # the body must not been compressed
                assert 'content-encoding' not in headers
                initial_message = msg
            elif msg_type == 'http.response.body':
                body = msg.get('body', b'')
                # the body should not be empty
                assert body != b''
                more_body = msg.get('more_body', False)
                # the body should not been read in streaming
                assert more_body is False
                # replace base href
                root_path = scope.get('root_path', '') or '/'
                body = body.replace(
                    b'<base href="/">', f'<base href="{root_path}">'.encode(), 1
                )
                msg['body'] = body
                # update content length
                headers = MutableHeaders(raw=initial_message['headers'])
                headers['Content-Length'] = str(len(body))
                # send messages
                await send(initial_message)
                await send(msg)
                # clean up
                del initial_message

        await self._app(scope, receive, _send)
