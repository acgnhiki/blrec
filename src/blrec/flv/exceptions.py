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
