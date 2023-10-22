from typing import Union

from blrec.flv.operators import MetaData as FLVMetaData
from blrec.hls.operators import MetaData as HLSMetaData

from .models import DanmuMsg, GiftSendMsg, GuardBuyMsg, SuperChatMsg, UserToastMsg

DanmakuMsg = Union[DanmuMsg, GiftSendMsg, GuardBuyMsg, SuperChatMsg, UserToastMsg]
MetaData = Union[FLVMetaData, HLSMetaData]
