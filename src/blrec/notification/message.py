
import humanize

from ..event import SpaceNoEnoughEventData

from ..bili.models import UserInfo, RoomInfo
from ..exception import format_exception


live_info_template = """
主播: {user_name}

标题: {room_title}

分区: {area_name}

房间: {room_id}
"""

disk_usage_template = """
路径: {path}

阈值: {threshold}

硬盘容量: {usage_total}

已用空间: {usage_used}

可用空间: {usage_free}
"""

exception_template = """
异常信息：

{exception_message}
"""


def make_live_info_content(user_info: UserInfo, room_info: RoomInfo) -> str:
    return live_info_template.format(
        user_name=user_info.name,
        room_title=room_info.title,
        area_name=room_info.area_name,
        room_id=room_info.room_id,
    )


def make_disk_usage_content(data: SpaceNoEnoughEventData) -> str:
    return disk_usage_template.format(
        path=data.path,
        threshold=humanize.naturalsize(data.threshold),
        usage_total=humanize.naturalsize(data.usage.total),
        usage_used=humanize.naturalsize(data.usage.used),
        usage_free=humanize.naturalsize(data.usage.free),
    )


def make_exception_content(exc: BaseException) -> str:
    return exception_template.format(
        exception_message=format_exception(exc),
    )
