from typing import Any, Dict, Literal, Mapping


ApiPlatform = Literal[
    'web',
    'android',
]

QualityNumber = Literal[
    20000,  # 4K
    10000,  # 原画
    401,    # 蓝光(杜比)
    400,    # 蓝光
    250,    # 超清
    150,    # 高清
    80,     # 流畅
]

StreamFormat = Literal[
    'flv',
    'ts',
    'fmp4',
]

StreamCodec = Literal[
    'avc',
    'hevc',
]

JsonResponse = Dict[str, Any]
ResponseData = Dict[str, Any]

Danmaku = Mapping[str, Any]
