import logging
import socket
import random
import re

from mebo.stream.decode import (
    RTPPacket,
    RTPDecodeError
)


logger = logging.getLogger(__name__)

MAX_TRIES = 3

SERVER_PORTS = re.compile(r'server_port=(?P<server_rtp>\d{4,5})-(?P<server_rtcp>\d{4,5})')


class RTPStream:

    TIMEOUT = 0
    START_BYTES = bytes([0xfe, 0xed, 0xfa, 0xce])
    RTCP_HEADER = [0x80, 0xc9, 0x0, 0x1]

    @staticmethod
    def choose_port(start=50000, end=60000):
        return random.randrange(start, end, 2)

    def __init__(self, sdp, host=None, timeout=15):
        self.sdp = sdp
        self.host = host or self.sdp.host_info
        self.name = self.sdp.control

        self._media = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._media.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_port = None

        self._rtcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rtcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_rtcp = None

        self._media.settimeout(timeout)
        self._rtcp.settimeout(timeout)

        tries = 0
        while tries < MAX_TRIES:
            try:
                self._media.bind(('', RTPStream.choose_port()))
                self._rtcp.bind(('', self.rtcp_port))
                break
            except Exception as e:
                logger.error('Failed to bind: %s', e)
                tries += 1
        else:
            raise Exception('Unable to bind port')

    def __repr__(self):
        return str(self)

    def __str__(self):
        return ':'.join([self.host, self.name])

    def setup(self, transport_header):
        match = SERVER_PORTS.search(transport_header)
        if not match:
            raise Exception('No server_ports found!')
        self.server_port, self.server_rtcp = map(int, match.groups())
        logger.debug('Server port for RTP on %s: %d', self.name, self.server_port)
        logger.debug('Server port for RTCP on %s: %d', self.name, self.server_rtcp)
        assert self._media.sendto(self.START_BYTES, (self.host, self.server_port))

    @property
    def transport(self):
        # could eventually get unicast info from stream itself maybe
        return f'{self.sdp.profile};unicast;client_port={self.media_port}-{self.rtcp_port}'

    @property
    def media_port(self):
        return self._media.getsockname()[1]

    @property
    def rtcp_port(self):
        return self.media_port + 1

    def capture(self, filename, seconds=None, bytes=None, packets=1000):
        capture_count = 0
        with open(filename, 'wb') as f:
            for i in range(packets):
                raw_packet = self._media.recv(4096)
                rtp = RTPPacket(raw_packet)
                try:
                    decoded = rtp.decode(self.sdp.name)
                    f.write(decoded)
                except RTPDecodeError as e:
                    logger.error('Unable to decode packet: %s', e)
                    continue
                capture_count += 1
        logger.debug('Captured %d packets in %s', capture_count, filename)
        return capture_count
