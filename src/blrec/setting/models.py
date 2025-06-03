from __future__ import annotations

import os
import re
from typing import ClassVar, Collection, Final, List, Optional, TypeVar

import toml
from pydantic import BaseModel as PydanticBaseModel
from pydantic import BaseSettings, Field, PrivateAttr, validator
from pydantic.networks import EmailStr, HttpUrl
from typing_extensions import Annotated

from blrec.bili.typing import QualityNumber, StreamFormat
from blrec.core.cover_downloader import CoverSaveStrategy
from blrec.logging.typing import LOG_LEVEL
from blrec.postprocess import DeleteStrategy
from blrec.utils.string import camel_case

from .typing import (
    BarkMessageType,
    EmailMessageType,
    MessageType,
    PushdeerMessageType,
    PushplusMessageType,
    RecordingMode,
    ServerchanMessageType,
    TelegramMessageType,
)

__all__ = (
    'DEFAULT_SETTINGS_FILE',
    'EnvSettings',
    'Settings',
    'SettingsIn',
    'SettingsOut',
    'BiliApiSettings',
    'HeaderOptions',
    'HeaderSettings',
    'DanmakuOptions',
    'DanmakuSettings',
    'RecorderOptions',
    'RecorderSettings',
    'PostprocessingSettings',
    'PostprocessingOptions',
    'TaskOptions',
    'TaskSettings',
    'OutputSettings',
    'LoggingSettings',
    'SpaceSettings',
    'EmailSettings',
    'ServerchanSettings',
    'PushdeerSettings',
    'PushplusSettings',
    'TelegramSettings',
    'BarkSettings',
    'NotifierSettings',
    'NotificationSettings',
    'EmailMessageTemplateSettings',
    'ServerchanMessageTemplateSettings',
    'PushdeerMessageTemplateSettings',
    'PushplusMessageTemplateSettings',
    'TelegramMessageTemplateSettings',
    'BarkMessageTemplateSettings',
    'EmailNotificationSettings',
    'ServerchanNotificationSettings',
    'PushdeerNotificationSettings',
    'PushplusNotificationSettings',
    'TelegramNotificationSettings',
    'BarkNotificationSettings',
    'WebHookSettings',
)


DEFAULT_OUT_DIR: Final[str] = os.environ.get('BLREC_DEFAULT_OUT_DIR', '.')
DEFAULT_LOG_DIR: Final[str] = os.environ.get('BLREC_DEFAULT_LOG_DIR', '~/.blrec/logs/')
DEFAULT_SETTINGS_FILE: Final[str] = os.environ.get(
    'BLREC_DEFAULT_SETTINGS_FILE', '~/.blrec/settings.toml'
)


class EnvSettings(BaseSettings):
    settings_file: Annotated[str, Field(env='BLREC_CONFIG')] = DEFAULT_SETTINGS_FILE
    out_dir: Annotated[Optional[str], Field(env='BLREC_OUT_DIR')] = None
    log_dir: Annotated[Optional[str], Field(env='BLREC_LOG_DIR')] = None
    api_key: Annotated[
        Optional[str],
        Field(
            env='BLREC_API_KEY',
            min_length=8,
            max_length=80,
            regex=r'[a-zA-Z\d\-]{8,80}',
        ),
    ] = None

    class Config:
        anystr_strip_whitespace = True


_V = TypeVar('_V')


class BaseModel(PydanticBaseModel):
    class Config:
        validate_assignment = True
        anystr_strip_whitespace = True
        allow_population_by_field_name = True

        @classmethod
        def alias_generator(cls, string: str) -> str:
            return camel_case(string)

    @staticmethod
    def _validate_with_collection(value: _V, allowed_values: Collection[_V]) -> None:
        if value not in allowed_values:
            raise ValueError(
                f'the value {value} does not be allowed, '
                f'must be one of {", ".join(map(str, allowed_values))}'
            )


class BiliApiSettings(BaseModel):
    base_api_urls: List[str] = ['https://api.bilibili.com']
    base_live_api_urls: List[str] = ['https://api.live.bilibili.com']
    base_play_info_api_urls: List[str] = ['https://api.live.bilibili.com']


class HeaderOptions(BaseModel):
    user_agent: Optional[str]
    cookie: Optional[str]


class HeaderSettings(HeaderOptions):
    user_agent: str = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'  # noqa
    )
    cookie: str = ''


class DanmakuOptions(BaseModel):
    danmu_uname: Optional[bool]
    record_gift_send: Optional[bool]
    record_free_gifts: Optional[bool]
    record_guard_buy: Optional[bool]
    record_super_chat: Optional[bool]
    save_raw_danmaku: Optional[bool]


class DanmakuSettings(DanmakuOptions):
    danmu_uname: bool = False
    record_gift_send: bool = True
    record_free_gifts: bool = True
    record_guard_buy: bool = True
    record_super_chat: bool = True
    save_raw_danmaku: bool = False


class RecorderOptions(BaseModel):
    stream_format: Optional[StreamFormat]
    recording_mode: Optional[RecordingMode]
    quality_number: Optional[QualityNumber]
    fmp4_stream_timeout: Optional[int]
    read_timeout: Optional[int]  # seconds
    disconnection_timeout: Optional[int]  # seconds
    buffer_size: Annotated[  # bytes
        Optional[int], Field(ge=4096, le=1024**2 * 512, multiple_of=2)
    ]
    save_cover: Optional[bool]
    cover_save_strategy: Optional[CoverSaveStrategy]

    @validator('fmp4_stream_timeout')
    def _validate_fmp4_stream_timeout(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            allowed_values = frozenset((3, 5, 10, 30, 60, 180, 300, 600))
            cls._validate_with_collection(v, allowed_values)
        return v

    @validator('read_timeout')
    def _validate_read_timeout(cls, value: Optional[int]) -> Optional[int]:
        if value is not None:
            allowed_values = frozenset((3, 5, 10, 30, 60, 180, 300, 600))
            cls._validate_with_collection(value, allowed_values)
        return value

    @validator('disconnection_timeout')
    def _validate_disconnection_timeout(cls, value: Optional[int]) -> Optional[int]:
        if value is not None:
            allowed_values = frozenset(60 * i for i in (3, 5, 10, 15, 20, 30))
            cls._validate_with_collection(value, allowed_values)
        return value


class RecorderSettings(RecorderOptions):
    stream_format: StreamFormat = 'flv'
    recording_mode: RecordingMode = 'standard'
    quality_number: QualityNumber = 20000  # 4K, the highest quality.
    fmp4_stream_timeout: int = 10
    read_timeout: int = 3
    disconnection_timeout: int = 600
    buffer_size: Annotated[int, Field(ge=4096, le=1024**2 * 512, multiple_of=2)] = 8192
    save_cover: bool = False
    cover_save_strategy: CoverSaveStrategy = CoverSaveStrategy.DEFAULT


class PostprocessingOptions(BaseModel):
    remux_to_mp4: Optional[bool]
    inject_extra_metadata: Optional[bool]
    delete_source: Optional[DeleteStrategy]


class PostprocessingSettings(PostprocessingOptions):
    remux_to_mp4: bool = False
    inject_extra_metadata: bool = True
    delete_source: DeleteStrategy = DeleteStrategy.AUTO


class OutputOptions(BaseModel):
    path_template: Optional[str]
    filesize_limit: Optional[int]  # file size in bytes
    duration_limit: Optional[int]  # duration in seconds

    @validator('path_template')
    def _validate_path_template(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            pattern = r'''^
                (?:
                    [^\\/:*?"<>|\t\n\r\f\v\{\}]*?
                    \{
                    (?:
                        roomid|uname|title|area|parent_area|
                        year|month|day|hour|minute|second
                    )
                    \}
                    [^\\/:*?"<>|\t\n\r\f\v\{\}]*?
                )+?
                (?:
                    /
                    (?:
                        [^\\/:*?"<>|\t\n\r\f\v\{\}]*?
                        \{
                        (?:
                            roomid|uname|title|area|parent_area|
                            year|month|day|hour|minute|second
                        )
                        \}
                        [^\\/:*?"<>|\t\n\r\f\v\{\}]*?
                    )+?
                )*
            $'''
            if not re.fullmatch(pattern, value, re.VERBOSE):
                raise ValueError(f"invalid path template: '{value}'")
        return value

    @validator('filesize_limit')
    def _validate_filesize_limit(cls, value: Optional[int]) -> Optional[int]:
        # file size in bytes, 0 indicates not limit。
        if value is not None:
            if not (0 <= value <= 1073731086581):  # 1073731086581(999.99 GB)
                raise ValueError(
                    'The filesize limit must be in the range of 0 to 1073731086581'
                )
        return value

    @validator('duration_limit')
    def _validate_duration_limit(cls, value: Optional[int]) -> Optional[int]:
        # duration in seconds, 0 indicates not limit。
        if value is not None:
            if not (0 <= value <= 359999):  # 359999(99:59:59)
                raise ValueError(
                    'The duration limit must be in the range of 0 to 359999'
                )
        return value


def out_dir_factory() -> str:
    path = os.path.normpath(os.path.expanduser(DEFAULT_OUT_DIR))
    os.makedirs(path, exist_ok=True)
    return path


class OutputSettings(OutputOptions):
    out_dir: Annotated[str, Field(default_factory=out_dir_factory)]
    path_template: str = (
        '{roomid} - {uname}/'
        'blive_{roomid}_{year}-{month}-{day}-{hour}{minute}{second}'
    )
    filesize_limit: int = 0  # no limit by default
    duration_limit: int = 0  # no limit by default

    @validator('out_dir')
    def _validate_dir(cls, path: str) -> str:
        if not os.path.isdir(os.path.expanduser(path)):
            raise ValueError(f"'{path}' not a directory")
        return path


class TaskOptions(BaseModel):
    output: OutputOptions = OutputOptions()
    header: HeaderOptions = HeaderOptions()
    danmaku: DanmakuOptions = DanmakuOptions()
    recorder: RecorderOptions = RecorderOptions()
    postprocessing: PostprocessingOptions = PostprocessingOptions()

    @classmethod
    def from_settings(cls, settings: TaskSettings) -> TaskOptions:
        return cls(
            **settings.dict(
                include={'output', 'header', 'danmaku', 'recorder', 'postprocessing'}
            )
        )


class TaskSettings(TaskOptions):
    # must use the real room id rather than the short room id!
    room_id: Annotated[int, Field(ge=1, lt=2**100)]
    enable_monitor: bool = True
    enable_recorder: bool = True


def log_dir_factory() -> str:
    path = os.path.normpath(os.path.expanduser(DEFAULT_LOG_DIR))
    os.makedirs(path, exist_ok=True)
    return path


class LoggingSettings(BaseModel):
    log_dir: Annotated[str, Field(default_factory=log_dir_factory)]
    console_log_level: LOG_LEVEL = 'INFO'
    backup_count: Annotated[int, Field(ge=0, le=90)] = 30

    @validator('log_dir')
    def _validate_dir(cls, path: str) -> str:
        if not os.path.isdir(os.path.expanduser(path)):
            raise ValueError(f"'{path}' not a directory")
        return path


class SpaceSettings(BaseModel):
    check_interval: int = 60  # 1 minutes
    space_threshold: int = 1024**3  # 1 GB
    recycle_records: bool = False

    @validator('check_interval')
    def _validate_interval(cls, value: int) -> int:
        allowed_values = frozenset((0, 10, 30, *(60 * i for i in (1, 3, 5, 10))))
        cls._validate_with_collection(value, allowed_values)
        return value

    @validator('space_threshold')
    def _validate_threshold(cls, value: int) -> int:
        allowed_values = frozenset(1024**3 * i for i in (1, 3, 5, 10, 20))
        cls._validate_with_collection(value, allowed_values)
        return value


class EmailSettings(BaseModel):
    src_addr: Annotated[str, EmailStr] = ''
    dst_addr: Annotated[str, EmailStr] = ''
    auth_code: str = ''
    smtp_host: str = 'smtp.163.com'
    smtp_port: int = 465


class ServerchanSettings(BaseModel):
    sendkey: str = ''

    @validator('sendkey')
    def _validate_sendkey(cls, value: str) -> str:
        if value != '' and not re.fullmatch(r'[a-zA-Z\d]+', value):
            raise ValueError('sendkey is invalid')
        return value


class PushdeerSettings(BaseModel):
    server: str = ''
    pushkey: str = ''

    @validator('server')
    def _validate_server(cls, value: str) -> str:
        if value != '' and not re.fullmatch(r'https?://.+', value):
            raise ValueError('server is invalid')
        return value

    @validator('pushkey')
    def _validate_pushkey(cls, value: str) -> str:
        if value != '' and not re.fullmatch(
            r'PDU\d+T[a-zA-Z\d]{32}(,PDU\d+T[a-zA-Z\d]{32}){0,99}', value
        ):
            raise ValueError('pushkey is invalid')
        return value


class PushplusSettings(BaseModel):
    token: str = ''
    topic: str = ''

    @validator('token')
    def _validate_token(cls, value: str) -> str:
        if value != '' and not re.fullmatch(r'[a-z\d]{32}', value):
            raise ValueError('token is invalid')
        return value


class TelegramSettings(BaseModel):
    token: str = ''
    chatid: str = ''
    server: str = ''

    @validator('token')
    def _validate_token(cls, value: str) -> str:
        if value != '' and not re.fullmatch(r'[0-9]{8,10}:[a-zA-Z0-9_-]{35}', value):
            raise ValueError('token is invalid')
        return value

    @validator('chatid')
    def _validate_chatid(cls, value: str) -> str:
        if value != '' and not re.fullmatch(r'(-|[0-9]){0,}', value):
            raise ValueError('chatid is invalid')
        return value

    @validator('server')
    def _validate_server(cls, value: str) -> str:
        if value != '' and not re.fullmatch(
            r'^https?:\/\/[a-zA-Z0-9-_.]+(:[0-9]+)?', value
        ):
            raise ValueError('server is invalid')
        return value


class BarkSettings(BaseModel):
    server: str = ''
    pushkey: str = ''

    @validator('server')
    def _validate_server(cls, value: str) -> str:
        if value != '' and not re.fullmatch(r'https?://.+', value):
            raise ValueError('server is invalid')
        return value

    @validator('pushkey')
    def _validate_pushkey(cls, value: str) -> str:
        if value != '' and not re.fullmatch(r'[a-zA-Z\d]+', value):
            raise ValueError('pushkey is invalid')
        return value


class NotifierSettings(BaseModel):
    enabled: bool = False


class NotificationSettings(BaseModel):
    notify_began: bool = True
    notify_ended: bool = True
    notify_error: bool = True
    notify_space: bool = True


class MessageTemplateSettings(BaseModel):
    began_message_type: MessageType
    began_message_title: str
    began_message_content: str
    ended_message_type: MessageType
    ended_message_title: str
    ended_message_content: str
    space_message_type: MessageType
    space_message_title: str
    space_message_content: str
    error_message_type: MessageType
    error_message_title: str
    error_message_content: str


class EmailMessageTemplateSettings(MessageTemplateSettings):
    began_message_type: EmailMessageType = 'html'
    began_message_title: str = ''
    began_message_content: str = ''
    ended_message_type: EmailMessageType = 'html'
    ended_message_title: str = ''
    ended_message_content: str = ''
    space_message_type: EmailMessageType = 'html'
    space_message_title: str = ''
    space_message_content: str = ''
    error_message_type: EmailMessageType = 'html'
    error_message_title: str = ''
    error_message_content: str = ''


class ServerchanMessageTemplateSettings(MessageTemplateSettings):
    began_message_type: ServerchanMessageType = 'markdown'
    began_message_title: str = ''
    began_message_content: str = ''
    ended_message_type: ServerchanMessageType = 'markdown'
    ended_message_title: str = ''
    ended_message_content: str = ''
    space_message_type: ServerchanMessageType = 'markdown'
    space_message_title: str = ''
    space_message_content: str = ''
    error_message_type: ServerchanMessageType = 'markdown'
    error_message_title: str = ''
    error_message_content: str = ''


class PushdeerMessageTemplateSettings(MessageTemplateSettings):
    began_message_type: PushdeerMessageType = 'markdown'
    began_message_title: str = ''
    began_message_content: str = ''
    ended_message_type: PushdeerMessageType = 'markdown'
    ended_message_title: str = ''
    ended_message_content: str = ''
    space_message_type: PushdeerMessageType = 'markdown'
    space_message_title: str = ''
    space_message_content: str = ''
    error_message_type: PushdeerMessageType = 'markdown'
    error_message_title: str = ''
    error_message_content: str = ''


class PushplusMessageTemplateSettings(MessageTemplateSettings):
    began_message_type: PushplusMessageType = 'markdown'
    began_message_title: str = ''
    began_message_content: str = ''
    ended_message_type: PushplusMessageType = 'markdown'
    ended_message_title: str = ''
    ended_message_content: str = ''
    space_message_type: PushplusMessageType = 'markdown'
    space_message_title: str = ''
    space_message_content: str = ''
    error_message_type: PushplusMessageType = 'markdown'
    error_message_title: str = ''
    error_message_content: str = ''


class TelegramMessageTemplateSettings(MessageTemplateSettings):
    began_message_type: TelegramMessageType = 'html'
    began_message_title: str = ''
    began_message_content: str = ''
    ended_message_type: TelegramMessageType = 'html'
    ended_message_title: str = ''
    ended_message_content: str = ''
    space_message_type: TelegramMessageType = 'html'
    space_message_title: str = ''
    space_message_content: str = ''
    error_message_type: TelegramMessageType = 'html'
    error_message_title: str = ''
    error_message_content: str = ''


class BarkMessageTemplateSettings(MessageTemplateSettings):
    began_message_type: BarkMessageType = 'markdown'
    began_message_title: str = ''
    began_message_content: str = ''
    ended_message_type: BarkMessageType = 'markdown'
    ended_message_title: str = ''
    ended_message_content: str = ''
    space_message_type: BarkMessageType = 'markdown'
    space_message_title: str = ''
    space_message_content: str = ''
    error_message_type: BarkMessageType = 'markdown'
    error_message_title: str = ''
    error_message_content: str = ''


class EmailNotificationSettings(
    EmailSettings, NotifierSettings, NotificationSettings, EmailMessageTemplateSettings
):
    pass


class ServerchanNotificationSettings(
    ServerchanSettings,
    NotifierSettings,
    NotificationSettings,
    ServerchanMessageTemplateSettings,
):
    pass


class PushdeerNotificationSettings(
    PushdeerSettings,
    NotifierSettings,
    NotificationSettings,
    PushplusMessageTemplateSettings,
):
    pass


class PushplusNotificationSettings(
    PushplusSettings,
    NotifierSettings,
    NotificationSettings,
    PushplusMessageTemplateSettings,
):
    pass


class TelegramNotificationSettings(
    TelegramSettings,
    NotifierSettings,
    NotificationSettings,
    TelegramMessageTemplateSettings,
):
    pass


class BarkNotificationSettings(
    BarkSettings, NotifierSettings, NotificationSettings, BarkMessageTemplateSettings
):
    pass


class WebHookEventSettings(BaseModel):
    live_began: bool = True
    live_ended: bool = True
    room_change: bool = True
    recording_started: bool = True
    recording_finished: bool = True
    recording_cancelled: bool = True
    video_file_created: bool = True
    video_file_completed: bool = True
    danmaku_file_created: bool = True
    danmaku_file_completed: bool = True
    raw_danmaku_file_created: bool = True
    raw_danmaku_file_completed: bool = True
    cover_image_downloaded: bool = True
    video_postprocessing_completed: bool = True
    postprocessing_completed: bool = True
    space_no_enough: bool = True
    error_occurred: bool = True


class WebHookSettings(WebHookEventSettings):
    url: Annotated[str, HttpUrl]


class Settings(BaseModel):
    _MAX_TASKS: ClassVar[int] = 100
    _MAX_WEBHOOKS: ClassVar[int] = 50

    _path: str = PrivateAttr()
    version: str = '1.0'

    tasks: Annotated[List[TaskSettings], Field(max_items=100)] = []
    output: OutputSettings = OutputSettings()  # type: ignore
    logging: LoggingSettings = LoggingSettings()  # type: ignore
    bili_api: BiliApiSettings = BiliApiSettings()
    header: HeaderSettings = HeaderSettings()
    danmaku: DanmakuSettings = DanmakuSettings()
    recorder: RecorderSettings = RecorderSettings()
    postprocessing: PostprocessingSettings = PostprocessingSettings()
    space: SpaceSettings = SpaceSettings()
    email_notification: EmailNotificationSettings = EmailNotificationSettings()
    serverchan_notification: ServerchanNotificationSettings = (
        ServerchanNotificationSettings()
    )
    pushdeer_notification: PushdeerNotificationSettings = PushdeerNotificationSettings()
    pushplus_notification: PushplusNotificationSettings = PushplusNotificationSettings()
    telegram_notification: TelegramNotificationSettings = TelegramNotificationSettings()
    bark_notification: BarkNotificationSettings = BarkNotificationSettings()
    webhooks: Annotated[List[WebHookSettings], Field(max_items=50)] = []

    @classmethod
    def load(cls, path: str) -> Settings:
        settings = cls.parse_obj(toml.load(path))
        settings._path = path
        return settings

    def update_from_env_settings(self, env_settings: EnvSettings) -> None:
        if (out_dir := env_settings.out_dir) is not None:
            self.output.out_dir = out_dir
        if (log_dir := env_settings.log_dir) is not None:
            self.logging.log_dir = log_dir

    def dump(self) -> None:
        assert self._path
        with open(self._path, 'wt', encoding='utf8') as file:
            toml.dump(self.dict(exclude_none=True), file)

    @validator('tasks')
    def _validate_tasks(cls, tasks: List[TaskSettings]) -> List[TaskSettings]:
        if len(tasks) > cls._MAX_TASKS:
            raise ValueError(f'Out of max tasks limits: {cls._MAX_TASKS}')
        return tasks

    @validator('webhooks')
    def _validate_webhooks(
        cls, webhooks: List[WebHookSettings]
    ) -> List[WebHookSettings]:
        if len(webhooks) >= cls._MAX_WEBHOOKS:
            raise ValueError(f'Out of max webhooks limits: {cls._MAX_WEBHOOKS}')
        return webhooks


class SettingsIn(BaseModel):
    output: Optional[OutputSettings] = None
    logging: Optional[LoggingSettings] = None
    bili_api: Optional[BiliApiSettings] = None
    header: Optional[HeaderSettings] = None
    danmaku: Optional[DanmakuSettings] = None
    recorder: Optional[RecorderSettings] = None
    postprocessing: Optional[PostprocessingSettings] = None
    space: Optional[SpaceSettings] = None
    email_notification: Optional[EmailNotificationSettings] = None
    serverchan_notification: Optional[ServerchanNotificationSettings] = None
    pushdeer_notification: Optional[PushdeerNotificationSettings] = None
    pushplus_notification: Optional[PushplusNotificationSettings] = None
    telegram_notification: Optional[TelegramNotificationSettings] = None
    bark_notification: Optional[BarkNotificationSettings] = None
    webhooks: Optional[List[WebHookSettings]] = None


class SettingsOut(SettingsIn):
    version: Optional[str] = None
    tasks: Optional[List[TaskSettings]] = None
