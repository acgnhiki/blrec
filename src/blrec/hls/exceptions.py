class SegmentDataCorrupted(ValueError):
    pass


class NoNewSegments(Exception):
    pass


class FetchSegmentError(Exception):
    pass
