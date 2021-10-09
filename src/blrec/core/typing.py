from typing import Union


from .models import DanmuMsg, GiftSendMsg, GuardBuyMsg, SuperChatMsg


DanmakuMsg = Union[
    DanmuMsg,
    GiftSendMsg,
    GuardBuyMsg,
    SuperChatMsg,
]
