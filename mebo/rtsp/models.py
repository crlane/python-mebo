import re

from collections import namedtuple

StatusLine = namedtuple('StatusLine', ['protocol', 'status_code', 'reason'])
NONCE_MATCHER = re.compile(r'nonce="(?P<digest_nonce>[a-f0-9]{64})"')


class RTSPRequest:

    def __init__(self, method, url, protocol, **headers):
        self.url = url
        self.method = method
        self._headers = headers
        self._command = ' '.join([method, url, protocol])

    @property
    def headers(self):
        if self._headers is None:
            self._headers = {}
        return self._headers

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

    Clones much OF the behavior of the requests' HTTPResponse object
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
    def nonce(self):
        try:
            digest_challenge_header = self.headers.get('WWW-Authenticate')
            match = NONCE_MATCHER.search(digest_challenge_header)
            if match:
                return match.group('digest_nonce')
        except KeyError:
            print(f'No challenge header found: {self.headers}!')
            raise

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
                header, value = re.split(r':\s?', line, maxsplit=1)
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
        return self.text.rpartition('\r\n\r\n')[-1]


class RTSPMediaError(Exception):
    pass
