from __future__ import annotations
import html
import asyncio
from typing import AsyncIterator, Final, List

from lxml import etree
import aiofiles

from .models import Metadata, Danmu
from .typing import Element


__all__ = 'DanmakuReader', 'DanmakuWriter'


class DanmakuReader:
    def __init__(self, path: str) -> None:
        self._path = path

    async def __aenter__(self) -> DanmakuReader:
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore
        pass

    async def init(self) -> None:
        loop = asyncio.get_running_loop()
        self._tree = await loop.run_in_executor(None, etree.parse, self._path)

    async def read_metadata(self) -> Metadata:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._read_metadata)

    async def read_danmus(self) -> AsyncIterator[Danmu]:
        for elem in await self._get_danmu_elems():
            yield self._make_danmu(elem)

    def _read_metadata(self) -> Metadata:
        return Metadata(
            user_name=self._tree.xpath('/i/metadata/user_name')[0].text,
            room_id=int(self._tree.xpath('/i/metadata/room_id')[0].text),
            room_title=self._tree.xpath('/i/metadata/room_title')[0].text,
            area=self._tree.xpath('/i/metadata/area')[0].text,
            parent_area=self._tree.xpath('/i/metadata/parent_area')[0].text,
            live_start_time=int(
                self._tree.xpath('/i/metadata/live_start_time')[0].text
            ),
            record_start_time=int(
                self._tree.xpath('/i/metadata/record_start_time')[0].text
            ),
            recorder=self._tree.xpath('/i/metadata/recorder')[0].text,
        )

    async def _get_danmu_elems(self) -> List[Element]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._tree.xpath, '/i/d')

    def _make_danmu(self, elem: Element) -> Danmu:
        params = elem.get('p').split(',')
        return Danmu(
            stime=float(params[0]),
            mode=int(params[1]),
            size=int(params[2]),
            color=int(params[3]),
            date=int(params[4]),
            pool=int(params[5]),
            uid=params[6],
            dmid=int(params[7]),
            text=elem.text,
        )


class DanmakuWriter:
    _XML_HEAD: Final[str] = """\
<?xml version="1.0" encoding="UTF-8"?>
<i>
    <chatserver>chat.bilibili.com</chatserver>
    <chatid>0</chatid>
    <mission>0</mission>
    <maxlimit>0</maxlimit>
    <state>0</state>
    <real_name>0</real_name>
    <source>e-r</source>
"""

    def __init__(self, path: str):
        self._path = path

    async def __aenter__(self) -> DanmakuWriter:
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore
        await self.complete()

    async def init(self) -> None:
        self._file = await aiofiles.open(self._path, 'wt', encoding='utf8')
        await self._file.write(self._XML_HEAD)

    async def write_metadata(self, metadata: Metadata) -> None:
        await self._file.write(self._serialize_metadata(metadata))

    async def write_danmu(self, danmu: Danmu) -> None:
        await self._file.write(self._serialize_danmu(danmu))

    async def complete(self) -> None:
        await self._file.write('</i>')
        await self._file.close()

    def _serialize_metadata(self, metadata: Metadata) -> str:
        return f"""\
    <metadata>
        <user_name>{html.escape(metadata.user_name)}</user_name>
        <room_id>{metadata.room_id}</room_id>
        <room_title>{html.escape(metadata.room_title)}</room_title>
        <area>{html.escape(metadata.area)}</area>
        <parent_area>{html.escape(metadata.parent_area)}</parent_area>
        <live_start_time>{metadata.live_start_time}</live_start_time>
        <record_start_time>{metadata.record_start_time}</record_start_time>
        <recorder>{metadata.recorder}</recorder>
    </metadata>
"""

    def _serialize_danmu(self, dm: Danmu) -> str:
        return (
            f'    <d p="{dm.stime:.5f},{dm.mode},{dm.size},{dm.color},'
            f'{dm.date},{dm.pool},{dm.uid},{dm.dmid}">'
            f'{html.escape(dm.text)}</d>\n'
        )
