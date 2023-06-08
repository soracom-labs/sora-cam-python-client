class SoraCamException(IOError):
    pass


class ExportFailedError(SoraCamException):
    pass


class ExportTimeoutError(SoraCamException):
    pass
