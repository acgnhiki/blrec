import logging
import asyncio
import smtplib
from abc import ABC, abstractmethod
from typing import TypedDict, cast, Literal
from email.message import EmailMessage
from http.client import HTTPException

import aiohttp

from ..utils.patterns import Singleton


__all__ = 'MessagingProvider', 'EmailService', 'Serverchan', 'Pushplus'


logger = logging.getLogger(__name__)


class MessagingProvider(Singleton, ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    async def send_message(self, title: str, content: str) -> None:
        ...


MSG_TYPE = Literal['plain', 'html']


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
        self, subject: str, content: str, msg_type: MSG_TYPE = 'plain'
    ) -> None:
        self._check_parameters()
        await asyncio.get_running_loop().run_in_executor(
            None, self._send_email, subject, content, msg_type
        )

    def _send_email(
        self, subject: str, content: str, msg_type: MSG_TYPE = 'plain'
    ) -> None:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.src_addr
        msg['To'] = self.dst_addr
        msg.set_content(content, subtype=msg_type, charset='utf-8')

        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as smtp:
            # smtp.set_debuglevel(1)
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

    async def send_message(self, title: str, content: str) -> None:
        self._check_parameters()
        await self._post_message(title, content)

    def _check_parameters(self) -> None:
        if not self.sendkey:
            raise ValueError('No sendkey supplied')

    async def _post_message(self, title: str, content: str) -> None:
        url = f'https://sctapi.ftqq.com/{self.sendkey}.send'
        payload = {'text': title, 'desp': content}

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.post(url, data=payload):
                pass


class PushplusResponse(TypedDict):
    code: int
    msg: str
    data: str


class Pushplus(MessagingProvider):
    url = 'http://pushplus.hxtrip.com/send'

    def __init__(self, token: str = '', topic: str = '') -> None:
        super().__init__()
        self.token = token
        self.topic = topic

    async def send_message(self, title: str, content: str) -> None:
        self._check_parameters()
        await self._post_message(title, content)

    def _check_parameters(self) -> None:
        if not self.token:
            raise ValueError('No token supplied')

    async def _post_message(self, title: str, content: str) -> None:
        payload = {
            'title': title,
            'content': content,
            'token': self.token,
            'topic': self.topic,
            'template': 'html',
        }

        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.post(self.url, json=payload) as res:
                response = cast(PushplusResponse, await res.json())
                if response['code'] != 200:
                    raise HTTPException(response['code'], response['msg'])
