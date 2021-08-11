
import attr


@attr.s(auto_attribs=True, slots=True, frozen=True)
class DiskUsage:
    total: int
    used: int
    free: int
