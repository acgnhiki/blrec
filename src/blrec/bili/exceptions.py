import attr
import aiohttp


@attr.s(auto_attribs=True, frozen=True, slots=True)
class ApiRequestError(Exception):
    code: int
    message: str


class DanmakuClientAuthError(aiohttp.ClientError):
    pass


class LiveRoomHidden(Exception):
    pass


class LiveRoomLocked(Exception):
    pass


class LiveRoomEncrypted(Exception):
    pass


class NoStreamAvailable(Exception):
    pass


class NoStreamFormatAvailable(Exception):
    pass


class NoStreamCodecAvailable(Exception):
    pass


class NoStreamQualityAvailable(Exception):
    pass


class NoAlternativeStreamAvailable(Exception):
    pass
