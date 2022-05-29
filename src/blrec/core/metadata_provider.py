from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict

from .. import __github__, __prog__, __version__
from ..bili.helpers import get_quality_name
from ..bili.live import Live

if TYPE_CHECKING:
    from .stream_recorder_impl import StreamRecorderImpl

__all__ = ('MetadataProvider',)


class MetadataProvider:
    def __init__(self, live: Live, stream_recorder: StreamRecorderImpl) -> None:
        super().__init__()
        self._live = live
        self._stream_recorder = stream_recorder

    def __call__(self) -> Dict[str, Any]:
        return self._make_metadata()

    def _make_metadata(self) -> Dict[str, Any]:
        live_start_time = datetime.fromtimestamp(
            self._live.room_info.live_start_time, timezone(timedelta(hours=8))
        )

        assert self._stream_recorder.real_quality_number is not None
        stream_quality = '{} ({}{})'.format(
            get_quality_name(self._stream_recorder.real_quality_number),
            self._stream_recorder.real_quality_number,
            ', bluray' if '_bluray' in self._stream_recorder.stream_url else '',
        )

        return {
            'Title': self._live.room_info.title,
            'Artist': self._live.user_info.name,
            'Date': str(live_start_time),
            'Comment': f'''\
B站直播录像
主播：{self._live.user_info.name}
标题：{self._live.room_info.title}
分区：{self._live.room_info.parent_area_name} - {self._live.room_info.area_name}
房间号：{self._live.room_info.room_id}
开播时间：{live_start_time}
流主机: {self._stream_recorder.stream_host}
流格式：{self._stream_recorder.stream_format}
流画质：{stream_quality}
录制程序：{__prog__} v{__version__} {__github__}''',
            'description': OrderedDict(
                {
                    'UserId': str(self._live.user_info.uid),
                    'UserName': self._live.user_info.name,
                    'RoomId': str(self._live.room_info.room_id),
                    'RoomTitle': self._live.room_info.title,
                    'Area': self._live.room_info.area_name,
                    'ParentArea': self._live.room_info.parent_area_name,
                    'LiveStartTime': str(live_start_time),
                    'StreamHost': self._stream_recorder.stream_host,
                    'StreamFormat': self._stream_recorder.stream_format,
                    'StreamQuality': stream_quality,
                    'Recorder': f'{__prog__} v{__version__} {__github__}',
                }
            ),
        }
