import socket
import random

MAX_TRIES = 3


class RTPStream:

    TIMEOUT = 0
    START_BYTES = 0xfeedface

    @staticmethod
    def choose_port(start=50000, end=60000):
        return random.randrange(start, end, 2)

    def __init__(self, sdp):
        self._media = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rtcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sdep = sdp
        tries = 0
        while tries < MAX_TRIES:
            try:
                self._media.bind(('', RTPStream.choose_port()))
                self._rtcp.bind(('', self.rtcp_port))
                break
            except Exception:
                tries += 1
        else:
            raise Exception('Unable to bind port')

    @property
    def media_port(self):
        return self._media.getsockname()[1]

    @property
    def rtcp_port(self):
        return self.media_port + 1
