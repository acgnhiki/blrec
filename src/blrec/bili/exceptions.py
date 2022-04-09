
import attr


@attr.s(auto_attribs=True, frozen=True, slots=True)
class ApiRequestError(Exception):
    code: int
    message: str


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
