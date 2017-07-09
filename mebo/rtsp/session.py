import random
import socket

from urllib.parse import urlsplit

from mebo.auth import response as gen_digest_response

from mebo.rtsp.models import (
    RTSPMediaError,
    RTSPResponse,
    RTSPRequest,
)

from mebo.rtsp import PROTOCOL_VERSION


class RTSPSession:

    USER_AGENT = 'com.skyrocket.srtmebo'

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
        self._session_id = None

        # private sockets
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.host, self.port))

    def digest_response(self, nonce, method):
        # HACK: they have a weird extra space at the end
        url_correction = self.url + ' '
        return gen_digest_response(nonce, self._username, self._realm, self._password, method, url_correction)

    def authorization(self, resp):
        """
        """
        assert resp.nonce
        username = f'Digest username="{self._username}"'
        realm = f'realm="{self._realm}"'
        nonce = f'nonce="{resp.nonce}"'
        uri = f'uri="{self.url + " "}"'
        nc = f'nc={self._nc:0>8}'
        cnonce = f'cnonce="{self._cnonce}"'
        qop = 'qop='
        response = f'response="{self.digest_response(resp.nonce, resp.request.method)}"'
        print(f'Got authorization response: {response}')
        opaque = 'opaque=""'
        msg = ','.join([username, realm, nonce, uri, nc, cnonce, qop, response, opaque])
        print(msg)
        return msg

    def _challenge(self, resp):
        """
        :param resp: The original response which issued the challenge nonce
        """
        if not resp.nonce:
            raise RTSPSessionError(f'Unable to find nonce in challenge header')
        self._cnonce = random.randrange(0, 10**8)
        resp.request.headers.update(**{'Authorization': self.authorization(resp)})
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
        print(f'Request sent: {request.raw_text}')
        bytes_sent = self._socket.send(request.raw_text)
        try:
            assert bytes_sent
            response = self._socket.recv(4096)
            print(f'Response received: {response}')
            resp = RTSPResponse(request, response)
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 401 and challenge:
                return self._challenge(resp)
            else:
                raise RTSPSessionError('Unable to complete digest challenge')
        finally:
            self._cseq += 1

    def options(self, **kwargs):
        # req = RTSPRequest(self.url, 'OPTIONS', **kwargs)
        # return self._request(req)
        raise NotImplementedError('Mebo RTSP server does not implement this')

    def describe(self, **kwargs):
        req = self._request_factory('DESCRIBE', self.url, **kwargs)
        return self._request(req)

    def setup(self, **kwargs):
        pass

    def play(self, **kwargs):
        pass

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
