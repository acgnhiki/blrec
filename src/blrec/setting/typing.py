from typing import AbstractSet, Literal, Union

RecordingMode = Literal['standard', 'raw']

TextMessageType = Literal['text']
HtmlMessageType = Literal['html']
MarkdownMessageType = Literal['markdown']
MessageType = Union[TextMessageType, MarkdownMessageType, HtmlMessageType]

EmailMessageType = Union[TextMessageType, HtmlMessageType]
ServerchanMessageType = MarkdownMessageType
PushdeerMessageType = Union[TextMessageType, MarkdownMessageType]
PushplusMessageType = Union[TextMessageType, MarkdownMessageType, HtmlMessageType]
TelegramMessageType = Union[MarkdownMessageType, HtmlMessageType]
BarkMessageType = Union[TextMessageType, MarkdownMessageType]


KeyOfSettings = Literal[
    'version',
    'tasks',
    'output',
    'logging',
    'bili_api',
    'header',
    'danmaku',
    'recorder',
    'postprocessing',
    'space',
    'email_notification',
    'serverchan_notification',
    'pushdeer_notification',
    'pushplus_notification',
    'telegram_notification',
    'bark_notification',
    'webhooks',
]

KeySetOfSettings = AbstractSet[KeyOfSettings]
