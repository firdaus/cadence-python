from cadence.frames import ErrorFrame

ERROR_INVALID = 0x00
ERROR_TIMEOUT = 0x01
ERROR_CANCELLED = 0x02
ERROR_BUSY = 0x03
ERROR_DECLINED = 0x04
ERROR_UNEXPECTED_ERROR = 0x05
ERROR_BAD_REQUEST = 0x06
ERROR_NETWORK_ERROR = 0x07
ERROR_UNHEALTHY = 0x08
ERROR_FATAL = 0x0FF


class TChannelException(Exception):

    def __init__(self, error_frame: ErrorFrame = None):
        self.error_frame = error_frame

    def __str__(self):
        return self.error_frame.message
