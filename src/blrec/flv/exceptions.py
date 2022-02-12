
class FlvDataError(ValueError):
    ...


class FlvHeaderError(FlvDataError):
    ...


class FlvTagError(FlvDataError):
    ...


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


class CutStream(Exception):
    ...
