from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


__all__ = (
    'ResponseMessage',
    'DataSelection',
    'AliasKeyOfSettings',
)


class ResponseMessage(BaseModel):
    code: int = 0
    message: str = ''
    data: Optional[Dict[str, Any]] = None


class DataSelection(str, Enum):
    ALL = 'all'

    # live status
    PREPARING = 'preparing'
    LIVING = 'living'
    ROUNDING = 'rounding'

    # task status
    MONITOR_ENABLED = 'monitor_enabled'
    MONITOR_DISABLED = 'monitor_disabled'
    RECORDER_ENABLED = 'recorder_enabled'
    RECORDER_DISABLED = 'recorder_disabled'

    # task running status
    STOPPED = 'stopped'
    WAITTING = 'waitting'
    RECORDING = 'recording'
    REMUXING = 'remuxing'
    INJECTING = 'injecting'


AliasKeyOfSettings = Literal[
    'version',
    'tasks',
    'output',
    'logging',
    'header',
    'danmaku',
    'recorder',
    'postprocessing',
    'space',
    'emailNotification',
    'serverchanNotification',
    'pushplusNotification',
    'webhooks',
]
