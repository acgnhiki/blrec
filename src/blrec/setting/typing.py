from typing import AbstractSet, Literal


KeyOfSettings = Literal[
    'version',
    'tasks',
    'output',
    'logging',
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
    'webhooks',
]

KeySetOfSettings = AbstractSet[KeyOfSettings]
