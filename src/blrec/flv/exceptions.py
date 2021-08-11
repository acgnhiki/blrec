

class FlvStreamCorruptedError(Exception):
    ...


class FlvFileCorruptedError(Exception):
    ...


class AudioParametersChanged(Exception):
    ...


class VideoParametersChanged(Exception):
    ...


class FileSizeOverLimit(Exception):
    ...


class DurationOverLimit(Exception):
    ...
