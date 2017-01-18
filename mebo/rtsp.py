from asyncio import (
    coroutine,
    open_connection,
    get_event_loop,
)

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
        self._loop = get_event_loop()
        self._loop.run_forever()
        self.reader, self.writer = self._connect()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._close()

    async def _connect(self):
        r, w = await open_connection(self.host, self.port, loop=self._loop)
        return r, w

    def _close():
        self.reader.close()
        self.writer.close()
        self._loop.stop()
        self._loop.close()

    async def _parse_headers(self)
        while True:
            line = await self.reader.readline()
            if not line: 
                # all headers processed, done
                break
            yield line.decode('ascii').rstrip()

    async def _parse_response(self):
        line = await self.reader.readline()
            
    async def _request(self, request):
        self.writer.writelines(request.text)
        resp = RTSPResponse(request)
        response = await self._parse_response()
        async for header in self._parse_headers():
            resp.headers.update([(k.strip(), v.strip()) for k, v in header.split(:)])

        return resp

    def options(self, **kwargs):
        req = RTSPRequest(self.url, 'OPTIONS', **kwargs)
        self._request(req)

    def describe(self, **kwargs):
        pass

    def setup(self, **kwargs):
        pass

    def play(self, **kwargs):
        pass

    def pause(self, **kwargs):
        pass

    def record(self, **kwargs):
        pass
