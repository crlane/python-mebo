import logging
import random
import socket
import threading

from urllib.parse import urlsplit, urljoin

from mebo.stream.auth import challenge_response

from mebo.stream.rtp import (
    RTPStream
)

from mebo.stream.sdp import (
    SDP
)


from mebo.stream.rtsp import (
    RTSPResponse,
    RTSPRequest,
)

from mebo.stream import PROTOCOL_VERSION

logger = logging.getLogger(__name__)


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
        self._cseq = 1

        # private sockets for rtsp
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.host, self.port))

        # rtp info
        self._session_id = None
        self.audio_stream = None
        self.video_stream = None

    def digest_response(self, nonce, method):
        return challenge_response(nonce, self._username, self._realm, self._password, method, self.url)

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

    def start_streams(self):

        desc = self.describe()
        self._cseq += 1
        logger.debug('SDP: %s', desc.body)
        self.sdp = SDP(desc.body)
        self.streams = [RTPStream(media_desc, host=self.host) for media_desc in self.sdp.media]

        for stream in self.streams:
            extra_headers = {'Transport': stream.transport}
            if self._session_id is not None:
                extra_headers.update({'Session': self._session_id})
            track = self.setup(urljoin(self.url, stream.name), **extra_headers)
            assert track.status_code == 200
            logger.debug('%s response body: %s', stream.name, track.lines)
            track_id = track.headers.get('Session')
            logger.debug('Track session id: %s', track_id)
            if self._session_id is None:
                self._session_id = track_id
            elif self._session_id != track_id:
                logger.warning('Got an extra session id: %s', self._session_id)
            self._cseq += 1
            stream.setup(track.headers.get('Transport'))

        logger.debug('RTP streams established: %s', self.streams)

        if self.streams:
            play_response = self.play(**{'Session': self._session_id, 'Range': 'npt=0.000-'})
            assert play_response.status_code == 200
            self._cseq += 1
            logger.debug('Play response: %s', play_response.lines)

            for stream in self.streams:
                ext = 'h264' if stream.sdp.name == 'video' else 'g711a'
                name = f'{stream.sdp}.{stream.sdp.control}.{ext}'
                t = threading.Thread(name=f'{stream.sdp.name}-thread', target=stream.capture, args=(name,), kwargs=dict(packets=4000))
                t.start()

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
        raise NotImplementedError

    def teardown(self, **kwargs):
        raise NotImplementedError

    def record(self, **kwargs):
        raise NotImplementedError


class RTSPSessionConfigurationError(Exception):
    pass


class RTSPSessionError(Exception):
    pass


class DigestChallengeError(Exception):
    pass
