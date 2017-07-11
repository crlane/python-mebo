import re
import socket
import random

MAX_TRIES = 3


class RTPStream:

    TIMEOUT = 0
    START_BYTES = bytes([0xfe, 0xed, 0xfa, 0xce])
    RTCP_HEADER = [0x80, 0xc9, 0x0, 0x1]

    @staticmethod
    def choose_port(start=50000, end=60000):
        return random.randrange(start, end, 2)

    def __init__(self, sdp):
        self.sdp = sdp

        self._client_media = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._client_rtcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self._server_media = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._server_rtcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self._client_media.settimeout(15)
        self._client_rtcp.settimeout(15)

        tries = 0
        while tries < MAX_TRIES:
            try:
                self._client_media.bind(('', RTPStream.choose_port()))
                self._client_rtcp.bind(('', self.rtcp_port))
                break
            except Exception as e:
                print(f'Failed to bind: {e}')
                tries += 1
        else:
            raise Exception('Unable to bind port')

    @property
    def media_port(self):
        return self._client_media.getsockname()[1]

    @property
    def rtcp_port(self):
        return self.media_port + 1

    def connect(self, host, remote_port, control=False):
        if not control:
            s = self._server_media
        else:
            s = self._server_rtcp
        s.connect((host, remote_port))

    def send(self, payload, control=False):
        if not control:
            s = self._server_media
        else:
            s = self._server_rtcp
        return s.send(payload)

    def receive(self, control=False):
        if not control:
            s = self._server_media
        else:
            s = self._server_rtcp
        return s.recv(4096)

    def capture(self, filename, seconds=None, bytes=None, packets=1000):
        with open(filename, 'wb') as f:
            for i in range(packets):
                print('Blocking...')
                packet = self._client_media.recv(4096)
                print(f'Packet received with {len(packet)} bytes')
                f.write(packet)
        print('Done capture')
