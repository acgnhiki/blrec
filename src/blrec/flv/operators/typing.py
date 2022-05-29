from typing import Union

from reactivex import Observable

from ..models import FlvHeader, FlvTag

FLVStreamItem = Union[FlvHeader, FlvTag]
FLVStream = Observable[FLVStreamItem]
