from asyncio import (
    coroutine,
    ensure_future,
    open_connection,
    get_event_loop,
)

from collections import namedtuple
from functools import partial
from urllib.parse import urlsplit

from mebo import __version__ as version

PROTOCOL_VERSION = 'RTSP/1.0'

RTSPStatus = namedtuple('RTSPStatus', ['url', 'code', 'description'])

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
        return (b.encode('utf-8') for b in self.text())

    def text(self):
        yield self._command
        for k, v in self.headers.items():
            yield '{}: {}'.format(k, v)


    def __repr__(self):
        return '{cls}: url:{url}, method:{method}, headers:{headers}, text:{text}'.format(
                cls=self.__class__,
                url=self.url,
                method=self.method,
                headers=self.headers,
                text=list(self.text()),
        )

class RTSPResponse:

    def __init__(self, request):
        self.request = request
        self.status = None
        self.headers = {}
        self.body = []

    def set_status(*args):
        self.status = RTSPStatus(*args)

    def __repr__(self):
        return '{cls}: request:{request}, status:{status}, headers:{headers}, body:{body}'.format(
                cls=self.__class__,
                request=self.request,
                status=self.status,
                headers=self.headers,
                body=self.body
        )

class RTSPSession:

    def __init__(self, url, port='', loop=None):
        self.url = url
        scheme, host, path, _, _ = urlsplit(url)
        self.host = host
        self.port = port or 554  # port 554 is default
        self._loop = loop or get_event_loop()
        self.reader = None
        self.writer = None
        self.executor(self._connect)
        self._id = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._close()

    async def _connect(self):
        print('Starting session: {}'.format(self))
        self.reader, self.writer = await open_connection(self.host, self.port, loop=self._loop)
        print('Session created: {}'.format(self))

    def _close():
        self.reader.close()
        self.writer.close()
        self._loop.close()

    def executor(self, coroutine):
        task = ensure_future(coroutine())
        self._loop.run_until_complete(task)
        return task.result

    async def _parse_headers(self):
        print('Waiting for headers...')
        while True:
            line = await self.reader.readline()
            if not line: 
                # all headers processed, done
                break
            print('Got line for header...')
            yield line.decode('utf-8').rstrip()

    async def _parse_response(self):
        print('Waiting for response...')
        line = await self.reader.readline()
        print('Response received: {}'.format(line))
        return line              

    async def _request(self, request):
        print('Sending request: {}'.format(request))
        self.writer.writelines(request.raw_text)
        resp = RTSPResponse(request)
        response = await self._parse_response()
        response.set_status(*response.split(' '))
        async for header in self._parse_headers():
            resp.headers.update([(k.strip(), v.strip()) for k, v in header.split(':')])
        return resp

    def options(self, **kwargs):
        req = RTSPRequest(self.url, 'OPTIONS', **kwargs)
        resp = self.executor(partial(self._request, req))
        return resp

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

    def __repr__(self):
        return '{cls}: host:{host}, port:{port}, reader:{reader}, writer:{writer}, loop:{loop}'.format(
                cls=self.__class__,
                host=self.host,
                port=self.port,
                reader=self.reader,
                writer=self.writer,
                loop=self._loop
        )
