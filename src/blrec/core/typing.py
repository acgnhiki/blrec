from typing import Union

from .models import DanmuMsg, GiftSendMsg, GuardBuyMsg, SuperChatMsg, UserToastMsg

DanmakuMsg = Union[DanmuMsg, GiftSendMsg, GuardBuyMsg, SuperChatMsg, UserToastMsg]
