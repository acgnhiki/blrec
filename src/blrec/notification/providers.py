import asyncio
import logging
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.message import EmailMessage
from http.client import HTTPException
from typing import Any, Dict, Final, TypedDict, cast
from urllib.parse import urljoin

import aiohttp

from ..setting.typing import (
    EmailMessageType,
    MessageType,
    PushdeerMessageType,
    PushplusMessageType,
    ServerchanMessageType,
    TelegramMessageType,
)
from ..utils.patterns import Singleton

__all__ = (
    'MessagingProvider',
    'EmailService',
    'Serverchan',
    'Pushdeer',
    'Pushplus',
    'Telegram',
)


logger = logging.getLogger(__name__)


class MessagingProvider(Singleton, ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    async def send_message(
        self, title: str, content: str, msg_type: MessageType
    ) -> None:
        ...


class EmailService(MessagingProvider):
    def __init__(
        self,
        src_addr: str = '',
        dst_addr: str = '',
        auth_code: str = '',
        smtp_host: str = 'smtp.163.com',
        smtp_port: int = 465,
    ) -> None:
        super().__init__()
        self.src_addr = src_addr
        self.dst_addr = dst_addr
        self.auth_code = auth_code
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    async def send_message(
        self, subject: str, content: str, msg_type: MessageType
    ) -> None:
        self._check_parameters()
        await asyncio.get_running_loop().run_in_executor(
            None, self._send_email, subject, content, msg_type
        )

    def _send_email(
        self, subject: str, content: str, msg_type: EmailMessageType
    ) -> None:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.src_addr
        msg['To'] = self.dst_addr
        subtype = 'html' if msg_type == 'html' else 'plain'
        msg.set_content(content, subtype=subtype, charset='utf-8')

        try:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as smtp:
                # smtp.set_debuglevel(1)
                smtp.login(self.src_addr, self.auth_code)
                smtp.send_message(msg, self.src_addr, self.dst_addr)
        except ssl.SSLError:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                # smtp.set_debuglevel(1)
                context = ssl.create_default_context()
                smtp.starttls(context=context)
                smtp.login(self.src_addr, self.auth_code)
                smtp.send_message(msg, self.src_addr, self.dst_addr)

    def _check_parameters(self) -> None:
        if not self.src_addr:
            raise ValueError('No source email address supplied')
        if not self.dst_addr:
            raise ValueError('No destination email address supplied')
        if not self.auth_code:
            raise ValueError('No auth code supplied')


class Serverchan(MessagingProvider):
    def __init__(self, sendkey: str = '') -> None:
        super().__init__()
        self.sendkey = sendkey

    async def send_message(
        self, title: str, content: str, msg_type: MessageType
    ) -> None:
        self._check_parameters()
        await self._post_message(title, content, cast(ServerchanMessageType, msg_type))

    def _check_parameters(self) -> None:
        if not self.sendkey:
            raise ValueError('No sendkey supplied')

    async def _post_message(
        self, title: str, content: str, msg_type: ServerchanMessageType
    ) -> None:
        url = f'https://sctapi.ftqq.com/{self.sendkey}.send'
        payload = {'text': title, 'desp': content}

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.post(url, data=payload):
                pass


class PushdeerResponse(TypedDict):
    code: int
    content: str
    error: str


class Pushdeer(MessagingProvider):
    _server: Final = 'https://api2.pushdeer.com'
    _endpoint: Final = '/message/push'

    def __init__(self, server: str = '', pushkey: str = '') -> None:
        super().__init__()
        self.server = server
        self.pushkey = pushkey

    async def send_message(
        self, title: str, content: str, msg_type: MessageType
    ) -> None:
        self._check_parameters()
        await self._post_message(title, content, cast(PushdeerMessageType, msg_type))

    def _check_parameters(self) -> None:
        if not self.pushkey:
            raise ValueError('No pushkey supplied')

    async def _post_message(
        self, title: str, content: str, msg_type: PushdeerMessageType
    ) -> None:
        url = urljoin(self.server or self._server, self._endpoint)
        payload = {
            'pushkey': self.pushkey,
            'text': title,
            'desp': content,
            'type': msg_type,
        }
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.post(url, json=payload) as res:
                response = cast(PushdeerResponse, await res.json())
                if response['code'] != 0:
                    raise HTTPException(response['code'], response['error'])


class PushplusResponse(TypedDict):
    code: int
    msg: str
    data: str


class Pushplus(MessagingProvider):
    url = 'http://www.pushplus.plus/send'

    def __init__(self, token: str = '', topic: str = '') -> None:
        super().__init__()
        self.token = token
        self.topic = topic

    async def send_message(
        self, title: str, content: str, msg_type: MessageType
    ) -> None:
        self._check_parameters()
        await self._post_message(title, content, msg_type)

    def _check_parameters(self) -> None:
        if not self.token:
            raise ValueError('No token supplied')

    async def _post_message(
        self, title: str, content: str, msg_type: PushplusMessageType
    ) -> None:
        payload = {
            'title': title,
            'content': content,
            'token': self.token,
            'topic': self.topic,
            'template': msg_type,
        }

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.post(self.url, json=payload) as res:
                response = cast(PushplusResponse, await res.json())
                if response['code'] != 200:
                    raise HTTPException(response['code'], response['msg'])


class TelegramResponse(TypedDict):
    ok: bool
    result: Dict[str, Any]


class Telegram(MessagingProvider):
    def __init__(self, token: str = '', chatid: str = '') -> None:
        super().__init__()
        self.token = token
        self.chatid = chatid

    async def send_message(
        self, title: str, content: str, msg_type: MessageType
    ) -> None:
        self._check_parameters()
        await self._post_message(title, content, cast(TelegramMessageType, msg_type))

    def _check_parameters(self) -> None:
        if not self.token:
            raise ValueError('No token supplied')
        if not self.chatid:
            raise ValueError('No chatid supplied')

    async def _post_message(
        self, title: str, content: str, msg_type: TelegramMessageType
    ) -> None:
        url = f'https://api.telegram.org/bot{self.token}/sendMessage'
        payload = {
            'chat_id': self.chatid,
            'text': title + '\n\n' + content,
            'parse_mode': 'MarkdownV2' if msg_type == 'markdown' else 'HTML',
        }

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.post(url, json=payload) as res:
                response = cast(TelegramResponse, await res.json())
                if not response['ok']:
                    raise HTTPException(
                        response['result']['error_code'],
                        response['result']['description'],
                    )
