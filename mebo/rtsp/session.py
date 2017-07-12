import logging
import os
import random
import re
import socket
import sys

from urllib.parse import urlsplit, urljoin

from mebo.auth import response as gen_digest_response

from mebo.rtsp.rtp import (
    RTPStream
)

from mebo.rtsp.models import (
    RTSPResponse,
    RTSPRequest,
)

from mebo.rtsp import PROTOCOL_VERSION

logger = logging.getLogger(__name__)
loglevel = getattr(logging, os.getenv('LOGLEVEL', 'INFO').upper())
logging.basicConfig(stream=sys.stdout, level=loglevel)

SERVER_PORTS = re.compile(r'server_port=(?P<server_rtp>\d{4,5})-(?P<server_rtcp>\d{4,5})')


class RTSPSession:

    USER_AGENT = 'python-mebo'

    def __init__(self, url, port=None, username=None, realm=None, password=None, user_agent=None):
        self.url = url
        scheme, host, path, _, _ = urlsplit(url)
        self.host = host
        self.port = port or 554  # port 554 is default
        if not user_agent:
            user_agent = RTSPSession.USER_AGENT
        self._user_agent = user_agent

        # Digest auth
        self._username = username
        if not username and realm:
            raise RTSPSessionConfigurationError('Must supply url, username, and realm')

        self._realm = realm
        self._password = password
        self._cnonce = None
        self._nc = 1
        self._opaque = ''
        self._cseq = 2

        # private sockets for rtsp
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.host, self.port))

        # rtp info
        self._session_id = None
        self.audio_stream = None
        self.video_stream = None

    def digest_response(self, nonce, method):
        return gen_digest_response(nonce, self._username, self._realm, self._password, method, self.url)

    def _authorization(self, resp):
        assert resp.nonce
        username = f'Digest username="{self._username}"'
        realm = f'realm="{self._realm}"'
        nonce = f'nonce="{resp.nonce}"'
        uri = f'uri="{self.url}"'
        nc = f'nc={self._nc:0>8}'
        cnonce = f'cnonce="{self._cnonce}"'
        qop = 'qop='
        response = f'response="{self.digest_response(resp.nonce, resp.request.method)}"'
        logger.debug(f'Got authorization response: {response}')
        opaque = 'opaque=""'
        msg = ','.join([username, realm, nonce, uri, nc, cnonce, qop, response, opaque])
        logger.debug(f'Message for challenge generated: {msg}')
        return msg

    def _challenge(self, resp):
        """
        :param resp: The original response which issued the challenge nonce
        """
        if not resp.nonce:
            raise RTSPSessionError(f'Unable to find nonce in challenge header')
        self._cnonce = random.randrange(0, 10**8)
        resp.request.headers.update(**{'Authorization': self._authorization(resp)})
        try:
            return self._request(resp.request, challenge=False)
        except Exception as e:
            raise DigestChallengeError('Unable to complete challenge')
        finally:
            self._nc += 1

    def _default_headers(self):
        return {
            'User-Agent': self._user_agent,
            'CSeq': self._cseq
        }

    def _request_factory(self, method, url, protocol=PROTOCOL_VERSION, **kwargs):
        h = self._default_headers()
        h.update(**kwargs)
        return RTSPRequest(method, url, protocol, **h)

    def _request(self, request, challenge=True):
        logger.debug('Request sent: %s', request.raw_text)
        bytes_sent = self._socket.send(request.raw_text)
        assert bytes_sent
        response = self._socket.recv(4096)
        logger.debug('Response received: %s', response)
        resp = RTSPResponse(request, response)
        if resp.status_code == 200:
            return resp
        elif resp.status_code == 401 and challenge:
            return self._challenge(resp)
        else:
            raise RTSPSessionError('Unable to complete digest challenge')

    def _init_server_stream(self, stream, transmission_header):
        match = SERVER_PORTS.search(transmission_header)
        if not match:
            raise Exception('No server_ports found!')
        server_port, server_rtcp = map(int, match.groups())
        logger.debug('SERVER PORT for RTP: %d', server_port)
        stream.connect(self.host, server_port)
        stream.connect(self.host, server_rtcp, control=True)
        assert stream.send(RTPStream.START_BYTES)

    def start_streams(self):

        desc = self.describe()
        self._cseq += 1
        logger.debug('SDP: %s', desc.body)
        self.video_stream = RTPStream(desc.body)
        self.audio_stream = RTPStream(desc.body)

        audio_options = f'RTP/AVP;unicast;client_port={self.audio_stream.media_port}-{self.audio_stream.rtcp_port}'
        video_options = f'RTP/AVP;unicast;client_port={self.video_stream.media_port}-{self.video_stream.rtcp_port}'

        video_track = self.setup(urljoin(self.url, 'track0'), **{'Transport': video_options})
        logger.debug('Video Track body: %s', video_track.lines)
        assert video_track.status_code == 200
        self._init_server_stream(self.video_stream, video_track.headers.get('Transport'))
        self._session_id = video_track.headers.pop('Session')

        audio_track = self.setup(urljoin(self.url, 'track1'), **{'Transport': audio_options, 'Session': self._session_id})
        logger.debug('Audio Track body: %s', audio_track.lines)
        self._cseq += 1
        assert audio_track.status_code == 200
        self._init_server_stream(self.audio_stream, audio_track.headers.get('Transport'))
        assert self._session_id == audio_track.headers.pop('Session')

        play_response = self.play(**{'Session': self._session_id, 'Range': 'npt=0.000-'})
        logger.debug('RTP streams established: %s', play_response)
        assert play_response.status_code == 200
        self._cseq += 1
        logger.debug('Play response: %s', play_response.lines)

        self.audio_stream.capture('audio_stream.pcap', packets=500)
        self.video_stream.capture('video_stream.pcap', packets=500)

    def options(self, **kwargs):
        # req = RTSPRequest(self.url, 'OPTIONS', **kwargs)
        # return self._request(req)
        raise NotImplementedError('Mebo RTSP server does not implement this')

    def describe(self, **kwargs):
        req = self._request_factory('DESCRIBE', self.url, **kwargs)
        return self._request(req)

    def setup(self, url, **kwargs):
        req = self._request_factory('SETUP', url, **kwargs)
        return self._request(req)

    def play(self, **kwargs):
        req = self._request_factory('PLAY', self.url, **{'Session': self._session_id, 'Range': 'npt=0.000-'})
        return self._request(req)

    def pause(self, **kwargs):
        pass

    def record(self, **kwargs):
        pass


class RTSPSessionConfigurationError(Exception):
    pass


class RTSPSessionError(Exception):
    pass


class DigestChallengeError(Exception):
    pass
