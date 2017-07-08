import re
import socket

from collections import namedtuple
from urllib.parse import urlsplit

StatusLine = namedtuple('StatusLine', ['protocol', 'status_code', 'reason'])

PROTOCOL_VERSION = 'RTSP/1.0'


class RTSPMediaError(Exception):
    pass


class RTSPRequest:

    def __init__(self, url, method, **headers):
        self.url = url
        self.method = method
        self._command = ' '.join([method, url, PROTOCOL_VERSION])
        self.headers.update(**headers)

        self._username = 'stream'
        self._realm = 'realm'
        self._cnonce = 4428977
        self._nc = 1
        self._response = '91b3cd804ec214aeaebfcf51306a093a'
        self._opaque = ''

    @property
    def headers(self):
        return {
            'User-Agent': 'com.skyrocket.srtmebo',
            'Accept': 'application/sdp',
            'CSeq': 1
        }

    def authorization(self, nonce):
        f'Digest username="{self._username}",realm="{self._realm}",nonce="{nonce}",uri={self.url},cnonce="{self._cnonce}",nc={self._nc},qop=,response="{self._response}",opaque="{self._opaque}"'

    @property
    def raw_text(self):
        string = '\r\n'.join(self.text())
        return bytes(string.encode('utf-8'))

    def text(self):
        yield self._command
        for header, value in self.headers.items():
            yield f'{header}: {value}'
        yield '\r\n'


class RTSPResponse:
    '''Represents responses for RTSP Negotiation

    Clones much of the behavior of the requests' HTTPResponse object
    '''

    def __init__(self, request, text, encoding='utf-8'):
        self.request = request
        self._raw = text

        self.encoding = encoding
        self.fallback = 'ascii'

        self._headers = {}
        self._status_line = None

    def __iter__(self):
        return self.iter_lines()

    def iter_lines(self):
        return (l.decode(self.encoding) for l in self._raw.splitlines())

    @property
    def lines(self):
        return list(self.iter_lines())

    @property
    def content(self):
        return self._raw

    @property
    def text(self):
        try:
            return self.content.decode(self.encoding)
        except UnicodeDecodeError:
            return self.content.decode(self.fallback)

    @property
    def _status(self):
        if self._status_line is None:
            self._status_line = StatusLine(*self.lines[0].split())
        return self._status_line

    @property
    def headers(self):
        if not self._headers:
            for line in self.lines[1:]:
                if not line:
                    break
                header, value = re.split(r':\s?', line)
                self._headers[header] = value
        return self._headers

    @property
    def reason(self):
        return self._status.reason

    @property
    def status_code(self):
        return int(self._status.status_code)

    @property
    def protocol(self):
        return self._status.protocol

    @property
    def body(self):
        return self.lines[-1]


class RTSPSession:

    def __init__(self, url, port=''):
        self.url = url
        scheme, host, path, _, _ = urlsplit(url)
        self.host = host
        self.port = port or 554  # port 554 is default
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.host, self.port))
        self._session_id = None

    def _request(self, request):
        bytes_sent = self._socket.send(request.raw_text)
        assert bytes_sent
        try:
            response = self._socket.recv(4096)
            print(response)
            return RTSPResponse(request, response)
        except Exception as e:
            raise RTSPMediaError(f'Unable to establish session {e}!')

    def options(self, **kwargs):
        # req = RTSPRequest(self.url, 'OPTIONS', **kwargs)
        # return self._request(req)
        raise NotImplementedError('Mebo RTSP server does not implement this')

    def describe(self, **kwargs):
        req = RTSPRequest(self.url, 'DESCRIBE', **kwargs)
        resp = self._request(req)
        if resp.status_code == 401:
            digest = req.headers.get('WWW-Authenticate')
            return self._request(RTSPRequest(self.url, 'DESCRIBE', **{'Authorization': digest}))
        else:
            return resp

    def setup(self, **kwargs):
        pass

    def play(self, **kwargs):
        pass

    def pause(self, **kwargs):
        pass

    def record(self, **kwargs):
        pass
