import asyncio
import json
import os
import struct
import zlib
from contextlib import suppress
from enum import Enum, IntEnum
from typing import Any, Dict, Final, List, Optional, Tuple, Union, cast

import aiohttp
import brotli
from aiohttp import ClientSession
from loguru import logger
from tenacity import retry, retry_if_exception_type, wait_exponential

from blrec.logging.context import async_task_with_logger_context

from ..event.event_emitter import EventEmitter, EventListener
from ..exception import exception_callback
from ..utils.mixins import AsyncStoppableMixin
from ..utils.string import extract_buvid_from_cookie, extract_uid_from_cookie
from .api import AppApi, WebApi
from .exceptions import DanmakuClientAuthError
from .typing import ApiPlatform, Danmaku

__all__ = 'DanmakuClient', 'DanmakuListener', 'Danmaku', 'DanmakuCommand'


class DanmakuListener(EventListener):
    async def on_client_connected(self) -> None:
        ...

    async def on_client_disconnected(self) -> None:
        ...

    async def on_client_reconnected(self) -> None:
        ...

    async def on_danmaku_received(self, danmu: Danmaku) -> None:
        ...

    async def on_error_occurred(self, error: Exception) -> None:
        ...


class DanmakuClient(EventEmitter[DanmakuListener], AsyncStoppableMixin):
    _HEARTBEAT_INTERVAL: Final[int] = 30

    def __init__(
        self,
        session: ClientSession,
        appapi: AppApi,
        webapi: WebApi,
        room_id: int,
        *,
        max_retries: int = 60,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__()
        self._logger_context = {'room_id': room_id}
        self._logger = logger.bind(**self._logger_context)

        self.session = session
        self.appapi = appapi
        self.webapi = webapi
        self._uid = 0
        self._buvid = ''
        self._room_id = room_id
        self.headers = headers or {}

        self._api_platform: ApiPlatform = 'web'
        self._danmu_info: Dict[str, Any] = COMMON_DANMU_INFO
        self._host_index: int = 0
        self._retry_delay: int = 0
        self._MAX_RETRIES: Final[int] = max_retries

        self._protover: int = WS.BODY_PROTOCOL_VERSION_BROTLI
        if ver := os.environ.get('BLREC_DANMAKU_PROTOCOL_VERSION'):
            if ver in (
                str(WS.BODY_PROTOCOL_VERSION_NORMAL),
                str(WS.BODY_PROTOCOL_VERSION_DEFLATE),
                str(WS.BODY_PROTOCOL_VERSION_BROTLI),
            ):
                self._protover = int(ver)
            else:
                self._logger.warning(
                    f'Invalid value of BLREC_DANMAKU_PROTOCOL_VERSION: {ver}'
                )
        self._logger.debug(f'protover: {self._protover}')

    @property
    def headers(self) -> Dict[str, str]:
        return self._headers

    @headers.setter
    def headers(self, value: Dict[str, str]) -> None:
        self._headers = {**value, 'Connection': 'Upgrade'}
        cookie = self._headers.get('Cookie', '')
        self._uid = extract_uid_from_cookie(cookie) or 0
        self._buvid = extract_buvid_from_cookie(cookie) or ''

    async def _do_start(self) -> None:
        await self._update_danmu_info()
        await self._connect()
        await self._create_message_loop()
        self._logger.debug('Started danmaku client')

    async def _do_stop(self) -> None:
        await self._terminate_message_loop()
        await self._disconnect()
        self._logger.debug('Stopped danmaku client')

    @async_task_with_logger_context
    async def restart(self) -> None:
        self._logger.debug('Restarting danmaku client...')
        await self.stop()
        await self.start()
        self._logger.debug('Restarted danmaku client')

    async def reconnect(self) -> None:
        if self.stopped:
            return

        self._logger.debug('Reconnecting...')
        await self._disconnect()
        await self._connect()
        await self._emit('client_reconnected')

    @retry(
        wait=wait_exponential(multiplier=0.1, max=10),
        retry=retry_if_exception_type(
            (asyncio.TimeoutError, aiohttp.ClientError, ConnectionError)
        ),
    )
    async def _connect(self) -> None:
        self._logger.debug('Connecting to server...')
        try:
            await self._connect_websocket()
            await self._send_auth()
            reply = await self._recieve_auth_reply()
            await self._handle_auth_reply(reply)
        except Exception:
            self._host_index += 1
            if self._host_index >= len(self._danmu_info['host_list']):
                self._host_index = 0
                # self._rotate_api_platform()  # XXX: use web api only
                await self._update_danmu_info()
            raise
        else:
            self._logger.debug('Connected to server')
            await self._emit('client_connected')

    async def _connect_websocket(self) -> None:
        url = 'wss://{}:{}/sub'.format(
            self._danmu_info['host_list'][self._host_index]['host'],
            self._danmu_info['host_list'][self._host_index]['wss_port'],
        )
        self._logger.debug(f'Connecting WebSocket... {url}')
        try:
            self._ws = await self.session.ws_connect(
                url, timeout=5, headers=self.headers
            )
        except Exception as exc:
            self._logger.debug(f'Failed to connect WebSocket: {repr(exc)}')
            raise
        else:
            self._logger.debug('Connected WebSocket')

    async def _send_auth(self) -> None:
        auth_msg = json.dumps(
            {
                "uid": self._uid,
                'roomid': self._room_id,  # must not be the short id!
                'protover': self._protover,
                "buvid": self._buvid,
                'platform': 'web',
                'type': 2,
                'key': self._danmu_info['token'],
            }
        )
        data = Frame.encode(WS.OP_USER_AUTHENTICATION, auth_msg)
        self._logger.debug('Sending user authentication...')
        try:
            await self._ws.send_bytes(data)
        except Exception as exc:
            self._logger.debug(f'Failed to sent user authentication: {repr(exc)}')
            raise
        else:
            self._logger.debug('Sent user authentication')

    async def _recieve_auth_reply(self) -> aiohttp.WSMessage:
        self._logger.debug('Receiving user authentication reply...')
        try:
            msg = await self._ws.receive(timeout=5)
            if msg.type != aiohttp.WSMsgType.BINARY:
                raise aiohttp.ClientError(msg)
        except Exception as exc:
            self._logger.debug(
                f'Failed to receive user authentication reply: {repr(exc)}'
            )
            raise
        else:
            self._logger.debug('Recieved user authentication reply')
            return msg

    async def _handle_auth_reply(self, reply: aiohttp.WSMessage) -> None:
        op, msg = Frame.decode(reply.data)
        assert op == WS.OP_CONNECT_SUCCESS
        msg = cast(str, msg)
        code = cast(int, json.loads(msg)['code'])

        if code == WS.AUTH_OK:
            self._logger.debug('Auth OK')
            self._create_heartbeat_task()
        elif code == WS.AUTH_TOKEN_ERROR:
            raise DanmakuClientAuthError(f'Token expired: {code}')
        else:
            raise DanmakuClientAuthError(f'Unexpected code: {code}')

    def _rotate_api_platform(self) -> None:
        if self._api_platform == 'android':
            self._api_platform = 'web'
        else:
            self._api_platform = 'android'

    async def _update_danmu_info(self) -> None:
        self._logger.debug(f'Updating danmu info via {self._api_platform} api...')
        api: Union[WebApi, AppApi]
        if self._api_platform == 'web':
            api = self.webapi
        else:
            api = self.appapi
        try:
            self._danmu_info = await api.get_danmu_info(self._room_id)
        except Exception as exc:
            self._logger.warning(f'Failed to update danmu info: {repr(exc)}')
            self._danmu_info = COMMON_DANMU_INFO
        else:
            self._logger.debug('Danmu info updated')

    async def _disconnect(self) -> None:
        await self._cancel_heartbeat_task()
        await self._close_websocket()
        self._logger.debug('Disconnected from server')
        await self._emit('client_disconnected')

    async def _close_websocket(self) -> None:
        with suppress(BaseException):
            await self._ws.close()

    def _create_heartbeat_task(self) -> None:
        self._heartbeat_task = asyncio.create_task(self._send_heartbeat())
        self._heartbeat_task.add_done_callback(exception_callback)

    async def _cancel_heartbeat_task(self) -> None:
        self._heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._heartbeat_task

    @async_task_with_logger_context
    async def _send_heartbeat(self) -> None:
        data = Frame.encode(WS.OP_HEARTBEAT, '')
        while True:
            try:
                await self._ws.send_bytes(data)
            except Exception as exc:
                self._logger.warning(f'Failed to send heartbeat: {repr(exc)}')
                await self._emit('error_occurred', exc)
                task = asyncio.create_task(self.restart())
                task.add_done_callback(exception_callback)
                break
            await asyncio.sleep(self._HEARTBEAT_INTERVAL)

    async def _create_message_loop(self) -> None:
        self._message_loop_task = asyncio.create_task(self._message_loop())
        self._message_loop_task.add_done_callback(exception_callback)
        self._logger.debug('Created message loop')

    async def _terminate_message_loop(self) -> None:
        self._message_loop_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._message_loop_task
        self._logger.debug('Terminated message loop')

    @async_task_with_logger_context
    async def _message_loop(self) -> None:
        while True:
            for msg in await self._receive():
                await self._dispatch_message(msg)

    async def _dispatch_message(self, msg: Dict[str, Any]) -> None:
        await self._emit('danmaku_received', msg)

    async def _receive(self) -> List[Dict[str, Any]]:
        self._reset_retry()

        while True:
            try:
                wsmsg = await self._ws.receive(timeout=self._HEARTBEAT_INTERVAL * 2)
            except Exception as e:
                await self._handle_receive_error(e)
            else:
                if wsmsg.type == aiohttp.WSMsgType.BINARY:
                    if result := await self._handle_data(wsmsg.data):
                        return result
                elif wsmsg.type == aiohttp.WSMsgType.ERROR:
                    await self._handle_receive_error(cast(Exception, wsmsg.data))
                elif wsmsg.type == aiohttp.WSMsgType.CLOSED:
                    msg = 'WebSocket Closed'
                    exc = aiohttp.WebSocketError(self._ws.close_code or 1006, msg)
                    await self._handle_receive_error(exc)
                else:
                    await self._handle_receive_error(ValueError(wsmsg))

    async def _handle_data(self, data: bytes) -> Optional[List[Dict[str, Any]]]:
        loop = asyncio.get_running_loop()

        try:
            op, msg = await loop.run_in_executor(None, Frame.decode, data)
            if op == WS.OP_MESSAGE:
                msg = cast(List[str], msg)
                return [json.loads(m) for m in msg]
            elif op == WS.OP_HEARTBEAT_REPLY:
                pass
        except Exception as e:
            self._logger.warning(
                f'Failed to handle data: {repr(e)}, data: {repr(data)}'
            )

        return None

    async def _handle_receive_error(self, exc: Exception) -> None:
        self._logger.warning(f'Failed to receive message: {repr(exc)}')
        await self._emit('error_occurred', exc)
        if isinstance(exc, asyncio.TimeoutError):
            return
        await self._retry()

    def _reset_retry(self) -> None:
        self._retry_count = 0
        self._retry_delay = 0

    async def _retry(self) -> None:
        if self._retry_count < self._MAX_RETRIES:
            if self._retry_delay > 0:
                self._logger.debug(
                    'Retry after {} second{}'.format(
                        self._retry_delay, 's' if self._retry_delay > 1 else ''
                    )
                )
                await asyncio.sleep(self._retry_delay)
            await self.reconnect()
            self._retry_count += 1
            self._retry_delay += 1
        else:
            raise aiohttp.WebSocketError(1006, 'Over the maximum of retries')


class Frame:
    HEADER_FORMAT = '>IHHII'

    @staticmethod
    def encode(op: int, msg: str) -> bytes:
        body = msg.encode()
        header_length = WS.PACKAGE_HEADER_TOTAL_LENGTH
        packet_length = header_length + len(body)
        ver = WS.HEADER_DEFAULT_VERSION
        seq = WS.HEADER_DEFAULT_SEQUENCE

        header = struct.pack(
            Frame.HEADER_FORMAT,
            packet_length,
            header_length,
            ver,  # protocal version
            op,  # operation
            seq,  # sequence id
        )

        return header + body

    @staticmethod
    def decode(data: bytes) -> Tuple[int, Union[int, str, List[str]]]:
        plen, hlen, ver, op, _ = struct.unpack_from(Frame.HEADER_FORMAT, data, 0)
        body = data[hlen:]

        if op == WS.OP_MESSAGE:
            if ver == WS.BODY_PROTOCOL_VERSION_BROTLI:
                data = brotli.decompress(body)
            elif ver == WS.BODY_PROTOCOL_VERSION_DEFLATE:
                data = zlib.decompress(body)
            elif ver == WS.BODY_PROTOCOL_VERSION_NORMAL:
                pass
            else:
                raise NotImplementedError(f'Unsupported protocol version: {ver}')

            msg_list = []
            offset = 0
            while offset < len(data):
                plen, hlen, ver, op, _ = struct.unpack_from(
                    Frame.HEADER_FORMAT, data, offset
                )
                body = data[hlen + offset : plen + offset]
                msg = body.decode('utf8')
                msg_list.append(msg)
                offset += plen

            return op, msg_list
        elif op == WS.OP_HEARTBEAT_REPLY:
            online_count = cast(int, struct.unpack('>I', body)[0])
            return op, online_count
        elif op == WS.OP_CONNECT_SUCCESS:
            auth_result = body.decode()
            return op, auth_result
        else:
            raise ValueError(f'Unexpected Operation: {op}')


class WS(IntEnum):
    OP_HEARTBEAT = 2
    OP_HEARTBEAT_REPLY = 3
    OP_MESSAGE = 5
    OP_USER_AUTHENTICATION = 7
    OP_CONNECT_SUCCESS = 8
    PACKAGE_HEADER_TOTAL_LENGTH = 16
    PACKAGE_OFFSET = 0
    HEADER_OFFSET = 4
    VERSION_OFFSET = 6
    OPERATION_OFFSET = 8
    SEQUENCE_OFFSET = 12
    BODY_PROTOCOL_VERSION_NORMAL = 0
    BODY_PROTOCOL_VERSION_DEFLATE = 2
    BODY_PROTOCOL_VERSION_BROTLI = 3
    HEADER_DEFAULT_VERSION = 1
    HEADER_DEFAULT_OPERATION = 1
    HEADER_DEFAULT_SEQUENCE = 1
    AUTH_OK = 0
    AUTH_TOKEN_ERROR = -101


class DanmakuCommand(Enum):
    ACTIVITY_MATCH_GIFT = 'ACTIVITY_MATCH_GIFT'
    ANCHOR_LOT_AWARD = 'ANCHOR_LOT_AWARD'
    ANCHOR_LOT_CHECKSTATUS = 'ANCHOR_LOT_CHECKSTATUS'
    ANCHOR_LOT_END = 'ANCHOR_LOT_END'
    ANCHOR_LOT_START = 'ANCHOR_LOT_START'
    ANIMATION = 'ANIMATION'
    BOX_ACTIVITY_START = 'BOX_ACTIVITY_START'
    CHANGE_ROOM_INFO = 'CHANGE_ROOM_INFO'
    CHASE_FRAME_SWITCH = 'CHASE_FRAME_SWITCH'
    COMBO_SEND = 'COMBO_SEND'
    CUT_OFF = 'CUT_OFF'
    DANMU_GIFT_LOTTERY_AWARD = 'DANMU_GIFT_LOTTERY_AWARD'
    DANMU_GIFT_LOTTERY_END = 'DANMU_GIFT_LOTTERY_END'
    DANMU_GIFT_LOTTERY_START = 'DANMU_GIFT_LOTTERY_START'
    DANMU_MSG = 'DANMU_MSG'
    ENTRY_EFFECT = 'ENTRY_EFFECT'
    GUARD_ACHIEVEMENT_ROOM = 'GUARD_ACHIEVEMENT_ROOM'
    GUARD_LOTTERY_START = 'GUARD_LOTTERY_START'
    HOUR_RANK_AWARDS = 'HOUR_RANK_AWARDS'
    LITTLE_TIPS = 'LITTLE_TIPS'
    LIVE = 'LIVE'
    LOL_ACTIVITY = 'LOL_ACTIVITY'
    LUCK_GIFT_AWARD_USER = 'LUCK_GIFT_AWARD_USER'
    MATCH_TEAM_GIFT_RANK = 'MATCH_TEAM_GIFT_RANK'
    MESSAGEBOX_USER_GAIN_MEDAL = 'MESSAGEBOX_USER_GAIN_MEDAL'
    NOTICE_MSG = 'NOTICE_MSG'
    PK_AGAIN = 'PK_AGAIN'
    PK_BATTLE_CRIT = 'PK_BATTLE_CRIT'
    PK_BATTLE_END = 'PK_BATTLE_END'
    PK_BATTLE_GIFT = 'PK_BATTLE_GIFT'
    PK_BATTLE_PRE = 'PK_BATTLE_PRE'
    PK_BATTLE_PRO_TYPE = 'PK_BATTLE_PRO_TYPE'
    PK_BATTLE_PROCESS = 'PK_BATTLE_PROCESS'
    PK_BATTLE_RANK_CHANGE = 'PK_BATTLE_RANK_CHANGE'
    PK_BATTLE_SETTLE_USER = 'PK_BATTLE_SETTLE_USER'
    PK_BATTLE_SPECIAL_GIFT = 'PK_BATTLE_SPECIAL_GIFT'
    PK_BATTLE_START = 'PK_BATTLE_START'
    PK_BATTLE_VOTES_ADD = 'PK_BATTLE_VOTES_ADD'
    PK_END = 'PK_END'
    PK_LOTTERY_START = 'PK_LOTTERY_START'
    PK_MATCH = 'PK_MATCH'
    PK_MIC_END = 'PK_MIC_END'
    PK_PRE = 'PK_PRE'
    PK_PROCESS = 'PK_PROCESS'
    PK_SETTLE = 'PK_SETTLE'
    PK_START = 'PK_START'
    PREPARING = 'PREPARING'
    RAFFLE_END = 'RAFFLE_END'
    RAFFLE_START = 'RAFFLE_START'
    ROOM_BLOCK_INTO = 'ROOM_BLOCK_INTO'
    ROOM_BLOCK_MSG = 'ROOM_BLOCK_MSG'
    ROOM_BOX_USER = 'ROOM_BOX_USER'
    ROOM_CHANGE = 'ROOM_CHANGE'
    ROOM_KICKOUT = 'ROOM_KICKOUT'
    ROOM_LIMIT = 'ROOM_LIMIT'
    ROOM_LOCK = 'ROOM_LOCK'
    ROOM_RANK = 'ROOM_RANK'
    ROOM_REAL_TIME_MESSAGE_UPDATE = 'ROOM_REAL_TIME_MESSAGE_UPDATE'
    ROOM_REFRESH = 'ROOM_REFRESH'
    ROOM_SILENT_OFF = 'ROOM_SILENT_OFF'
    ROOM_SILENT_ON = 'ROOM_SILENT_ON'
    ROOM_SKIN_MSG = 'ROOM_SKIN_MSG'
    SCORE_CARD = 'SCORE_CARD'
    SEND_GIFT = 'SEND_GIFT'
    SEND_TOP = 'SEND_TOP'
    SPECIAL_GIFT = 'SPECIAL_GIFT'
    SUPER_CHAT_ENTRANCE = 'SUPER_CHAT_ENTRANCE'
    SUPER_CHAT_MESSAGE = 'SUPER_CHAT_MESSAGE'
    SUPER_CHAT_MESSAGE_DELETE = 'SUPER_CHAT_MESSAGE_DELETE'
    TV_END = 'TV_END'
    TV_START = 'TV_START'
    USER_TOAST_MSG = 'USER_TOAST_MSG'
    VOICE_JOIN_STATUS = 'VOICE_JOIN_STATUS'
    WARNING = 'WARNING'
    WATCH_LPL_EXPIRED = 'WATCH_LPL_EXPIRED'
    WEEK_STAR_CLOCK = 'WEEK_STAR_CLOCK'
    WELCOME = 'WELCOME'
    WELCOME_GUARD = 'WELCOME_GUARD'
    WIN_ACTIVITY = 'WIN_ACTIVITY'
    WIN_ACTIVITY_USER = 'WIN_ACTIVITY_USER'
    WISH_BOTTLE = 'WISH_BOTTLE'
    GUARD_BUY = 'GUARD_BUY'
    # ...


COMMON_DANMU_INFO: Final[Dict[str, Any]] = {
    "token": "",
    "host_list": [
        {
            "host": "broadcastlv.chat.bilibili.com",
            "port": 2243,
            "wss_port": 443,
            "ws_port": 2244,
        }
    ],
}
