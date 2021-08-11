#!/usr/bin/env python3
import json
import struct
import zlib
import asyncio
import logging
from enum import IntEnum, Enum
from contextlib import suppress
from typing import Any, Dict, Final, Tuple, List, Union, cast, Optional

import aiohttp
from aiohttp import ClientSession
from tenacity import (
    retry,
    wait_exponential,
    retry_if_exception_type,
)

from .typing import Danmaku
from ..event.event_emitter import EventListener, EventEmitter
from ..exception import exception_callback
from ..utils.mixins import AsyncStoppableMixin
from ..logging.room_id import aio_task_with_room_id


__all__ = 'DanmakuClient', 'DanmakuListener', 'Danmaku', 'DanmakuCommand'


logger = logging.getLogger(__name__)


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
    _URL: Final[str] = 'wss://broadcastlv.chat.bilibili.com:443/sub'
    _HEARTBEAT_INTERVAL: Final[int] = 30

    def __init__(
        self,
        session: ClientSession,
        room_id: int,
        *,
        max_retries: int = 10,
    ) -> None:
        super().__init__()
        self.session = session
        self._room_id = room_id

        self._retry_delay: int = 0
        self._MAX_RETRIES: Final[int] = max_retries

    async def _do_start(self) -> None:
        await self._connect()
        await self._create_message_loop()
        logger.debug('Started danmaku client')

    async def _do_stop(self) -> None:
        await self._terminate_message_loop()
        await self._disconnect()
        logger.debug('Stopped danmaku client')

    async def reconnect(self) -> None:
        if self.stopped:
            return

        logger.debug('Reconnecting...')
        await self._disconnect()
        await self._connect()
        await self._emit('client_reconnected')

    @retry(
        wait=wait_exponential(multiplier=0.1, max=60),
        retry=retry_if_exception_type((
            asyncio.TimeoutError, aiohttp.ClientError,
        )),
    )
    async def _connect(self) -> None:
        logger.debug('Connecting to server...')
        await self._connect_websocket()
        await self._send_auth()
        reply = await self._recieve_auth_reply()
        self._handle_auth_reply(reply)
        logger.debug('Connected to server')
        await self._emit('client_connected')

    async def _connect_websocket(self) -> None:
        self._ws = await self.session.ws_connect(self._URL, timeout=5)
        logger.debug('Established WebSocket connection')

    async def _send_auth(self) -> None:
        auth_msg = json.dumps({
            'uid': 0,
            'roomid': self._room_id,  # must not be the short id!
            # 'protover': WS.BODY_PROTOCOL_VERSION_NORMAL,
            'protover': WS.BODY_PROTOCOL_VERSION_DEFLATE,
            'platform': 'web',
            'clientver': '1.1.031',
            'type': 2
        })
        data = Frame.encode(WS.OP_USER_AUTHENTICATION, auth_msg)
        await self._ws.send_bytes(data)
        logger.debug('Sent user authentication')

    async def _recieve_auth_reply(self) -> aiohttp.WSMessage:
        msg = await self._ws.receive(timeout=5)
        if msg.type != aiohttp.WSMsgType.BINARY:
            raise aiohttp.ClientError(msg)
        logger.debug('Recieved reply')
        return msg

    def _handle_auth_reply(self, reply: aiohttp.WSMessage) -> None:
        op, msg = Frame.decode(reply.data)
        assert op == WS.OP_CONNECT_SUCCESS
        msg = cast(str, msg)
        code = cast(int, json.loads(msg)['code'])

        if code == WS.AUTH_OK:
            logger.debug('Auth OK')
            self._create_heartbeat_task()
        elif code == WS.AUTH_TOKEN_ERROR:
            logger.debug('Auth Token Error')
            raise ValueError(f'Auth Token Error: {code}')
        else:
            raise ValueError(f'Unexpected code: {code}')

    async def _disconnect(self) -> None:
        await self._cancel_heartbeat_task()
        await self._close_websocket()
        logger.debug('Disconnected from server')
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

    @aio_task_with_room_id
    async def _send_heartbeat(self) -> None:
        data = Frame.encode(WS.OP_HEARTBEAT, '')
        while True:
            await self._ws.send_bytes(data)
            await asyncio.sleep(self._HEARTBEAT_INTERVAL)

    async def _create_message_loop(self) -> None:
        self._message_loop_task = asyncio.create_task(self._message_loop())
        self._message_loop_task.add_done_callback(exception_callback)
        logger.debug('Created message loop')

    async def _terminate_message_loop(self) -> None:
        self._message_loop_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._message_loop_task
        logger.debug('Terminated message loop')

    @aio_task_with_room_id
    async def _message_loop(self) -> None:
        while True:
            for msg in await self._receive():
                await self._dispatch_message(msg)

    async def _dispatch_message(self, msg: Dict[str, Any]) -> None:
        await self._emit('danmaku_received', msg)

    @retry(retry=retry_if_exception_type((asyncio.TimeoutError,)))
    async def _receive(self) -> List[Dict[str, Any]]:
        self._retry_count = 0
        self._retry_delay = 0

        while True:
            wsmsg = await self._ws.receive(timeout=self._HEARTBEAT_INTERVAL)

            if wsmsg.type == aiohttp.WSMsgType.BINARY:
                if (result := await self._handle_data(wsmsg.data)):
                    return result
            elif wsmsg.type == aiohttp.WSMsgType.ERROR:
                await self._handle_error(cast(Exception, wsmsg.data))
            elif wsmsg.type == aiohttp.WSMsgType.CLOSED:
                msg = 'WebSocket Closed'
                exc = aiohttp.WebSocketError(self._ws.close_code or 1006, msg)
                await self._handle_error(exc)
            else:
                raise ValueError(wsmsg)

    @staticmethod
    async def _handle_data(data: bytes) -> Optional[List[Dict[str, Any]]]:
        loop = asyncio.get_running_loop()
        op, msg = await loop.run_in_executor(None, Frame.decode, data)

        if op == WS.OP_MESSAGE:
            msg = cast(List[str], msg)
            return [json.loads(m) for m in msg]
        elif op == WS.OP_HEARTBEAT_REPLY:
            return None
        else:
            return None

    async def _handle_error(self, exc: Exception) -> None:
        logger.debug(f'Failed to receive message due to: {repr(exc)}')
        await self._emit('error_occurred', exc)
        await self._retry()

    async def _retry(self) -> None:
        if self._retry_count < self._MAX_RETRIES:
            if self._retry_delay > 0:
                logger.debug('Retry after {} second{}'.format(
                    self._retry_delay,
                    's' if self._retry_delay > 1 else '',
                ))
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
        plen, hlen, ver, op, _ = struct.unpack_from(
            Frame.HEADER_FORMAT, data, 0
        )
        body = data[hlen:]

        if op == WS.OP_MESSAGE:
            if ver == WS.BODY_PROTOCOL_VERSION_DEFLATE:
                data = zlib.decompress(body)

            msg_list = []
            offset = 0
            while offset < len(data):
                plen, hlen, ver, op, _ = struct.unpack_from(
                    Frame.HEADER_FORMAT, data, offset
                )
                body = data[hlen + offset:plen + offset]
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
    AUTH_OK = 0
    AUTH_TOKEN_ERROR = -101
    BODY_PROTOCOL_VERSION_DEFLATE = 2
    BODY_PROTOCOL_VERSION_NORMAL = 0
    HEADER_DEFAULT_OPERATION = 1
    HEADER_DEFAULT_SEQUENCE = 1
    HEADER_DEFAULT_VERSION = 1
    HEADER_OFFSET = 4
    OP_CONNECT_SUCCESS = 8
    OP_HEARTBEAT = 2
    OP_HEARTBEAT_REPLY = 3
    OP_MESSAGE = 5
    OP_USER_AUTHENTICATION = 7
    OPERATION_OFFSET = 8
    PACKAGE_HEADER_TOTAL_LENGTH = 16
    PACKAGE_OFFSET = 0
    SEQUENCE_OFFSET = 12
    VERSION_OFFSET = 6


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
    # ...


if __name__ == '__main__':
    def add_task_name(record: logging.LogRecord) -> bool:
        try:
            task = asyncio.current_task()
            assert task is not None
        except Exception:
            name = ''
        else:
            name = task.get_name()

        if '::' in name:
            record.roomid = '[' + name.split('::')[-1] + '] '  # type: ignore
        else:
            record.roomid = ''  # type: ignore

        return True

    def configure_logger() -> None:
        # config root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # config formatter
        fmt = '[%(asctime)s] [%(levelname)s] %(roomid)s%(message)s'
        formatter = logging.Formatter(fmt)

        # logging to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(add_task_name)
        logger.addHandler(console_handler)

    async def get_room_list(
        session: ClientSession, count: int = 99
    ) -> List[Dict[str, Any]]:
        url = 'https://api.live.bilibili.com/room/v3/area/getRoomList'
        params = {
            'platform': 'web',
            'parent_area_id': 1,
            'cate_id': 0,
            'area_id': 0,
            'sort_type': 'online',
            'page': 1,
            'page_size': count,
            'tag_version': 1,
        }
        async with session.get(url, params=params) as response:
            j = await response.json()
            return j['data']['list']

    class DanmakuPrinter(DanmakuListener):
        def __init__(
            self, danmaku_client: DanmakuClient, room_id: int
        ) -> None:
            self._danmaku_client = danmaku_client
            self._room_id = room_id

        async def enable(self) -> None:
            self._danmaku_client.add_listener(self)

        async def disable(self) -> None:
            self._danmaku_client.remove_listener(self)

        async def on_danmaku_received(self, danmu: Danmaku) -> None:
            json_string = json.dumps(danmu, ensure_ascii=False)
            logger.info(f'{json_string}')

    class DanmakuDumper(DanmakuListener):
        def __init__(
            self, danmaku_client: DanmakuClient, room_id: int
        ) -> None:
            self._danmaku_client = danmaku_client
            from datetime import datetime
            data_time_string = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self._filename = f'blive_cmd_{room_id}_{data_time_string}.jsonl'

        async def start(self) -> None:
            import aiofiles
            self._file = await aiofiles.open(
                self._filename, mode='wt', encoding='utf8'
            )
            logger.debug(f'Opened file: {self._filename}')
            self._danmaku_client.add_listener(self)

        async def stop(self) -> None:
            self._danmaku_client.remove_listener(self)
            await self._file.close()
            logger.debug(f'Closed file: {self._filename}')

        async def on_danmaku_received(self, danmu: Danmaku) -> None:
            json_string = json.dumps(danmu, ensure_ascii=False)
            await self._file.write(json_string + '\n')

    async def test_room(session: ClientSession, room_id: int) -> None:
        client = DanmakuClient(session, room_id)
        printer = DanmakuPrinter(client, room_id)
        dumper = DanmakuDumper(client, room_id)

        await printer.enable()
        await dumper.start()
        await client.start()

        keyboard_interrupt_event = asyncio.Event()
        try:
            await keyboard_interrupt_event.wait()
        finally:
            await client.stop()
            await dumper.stop()
            await printer.disable()

    async def test() -> None:
        import sys
        try:
            # the room id must not be the short id!
            room_ids = list(map(int, sys.argv[1:]))
        except ValueError:
            print('Usage: room_id, ...')
            sys.exit(0)

        configure_logger()

        async with ClientSession() as session:
            tasks = []

            if not room_ids:
                room_list = await get_room_list(session)
                room_ids = [room['roomid'] for room in room_list]

            logger.debug(f'room count: {len(room_ids)}')

            for room_id in room_ids:
                task = asyncio.create_task(
                    test_room(session, room_id), name=f'test_room::{room_id}',
                )
                tasks.append(task)

            await asyncio.wait(tasks)

    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        pass
