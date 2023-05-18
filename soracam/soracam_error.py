class SoraCamException(IOError):
    """There was an ambiguous exception that occurred while handling your
    request.
    """
    pass


class Timeout(SoraCamException):
    """The request timed out.
    """
    pass


class RequestFail(SoraCamException):
    """The request failed.
    """
    pass


class ExportFailedError(SoraCamException):
    pass


class ExportTimeoutError(SoraCamException):
    pass
