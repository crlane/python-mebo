import socket

from urllib.parse import urlsplit

from mebo import __version__ as version

PROTOCOL_VERSION = 'RTSP/1.0'


class RTSPRequest:

    def __init__(self, url, method, **headers):
        self.url = url
        self.method = method
        self._command = ' '.join([method, url, PROTOCOL_VERSION])
        self.headers.update(**headers)

    @property
    def headers(self):
        return { 
            'User-Agent': 'python-mebo v{}'.format(version),
            'Accept': 'application/sdp'
         }

    @property
    def raw_text(self):
        string = '\r\n'.join(self.text())
        return bytes(string.encode('utf-8'))

    def text(self):
        yield self._command
        for k, v in self.headers.items():
            yield '{}: {}'.format(k, v)


class RTSPResponse:

    def __init__(self, request):
        self.request = request
        self.status = []
        self.headers = {}
        self.body = []

class RTSPSession:

    def __init__(self, url, port=''):
        self.url = url
        scheme, host, path, _, _ = urlsplit(url)
        self.host = host
        self.port = port or 554  # port 554 is default
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.host, self.port))

    def _request(self, request):
        self._socket.send(request.raw_text)
        self._socket.settimeout(10)
        resp = RTSPResponse(request)
        while True:
            text = self._socket.recv(4096) 
            if not text:
                break
            lines = text.split('\r\n')
            resp.body.append(lines)
        return resp

    def options(self, **kwargs):
        # req = RTSPRequest(self.url, 'OPTIONS', **kwargs)
        # return self._request(req)
        raise NotImplementedError('Mebo RTSP server does not implement this')

    def describe(self, **kwargs):
        req = RTSPRequest(self.url, 'DESCRIBE', **kwargs)
        return self._request(req)

    def setup(self, **kwargs):
        pass

    def play(self, **kwargs):
        pass

    def pause(self, **kwargs):
        pass

    def record(self, **kwargs):
        pass
