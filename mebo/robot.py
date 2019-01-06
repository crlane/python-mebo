"""Classes and methods for working with the physical Mebo robot"""
import logging
import socket
import sys
import time
from abc import ABC
from collections import namedtuple
from functools import partial
from ipaddress import (
    AddressValueError,
    IPv4Network,
    IPv4Address
)

from xml.etree.ElementTree import fromstring as xmlfromstring

from requests import Session
from requests.exceptions import (
    ConnectionError,
    HTTPError
)

from zeroconf import ServiceBrowser, Zeroconf

from .exceptions import (
    MeboCommandError,
    MeboDiscoveryError,
    MeboRequestError,
    MeboConnectionError,
    MeboConfigurationError
)

from mebo.stream.session import (
    RTSPSession,
)


logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

Broadcast = namedtuple('Broadcast', ['ip', 'port', 'data'])
WirelessNetwork = namedtuple('WirelessNetwork', ['ssid', 'mac', 'a', 'q', 'si', 'nl', 'ch'])

NORTH = 'n'
NORTH_EAST = 'ne'
EAST = 'e'
SOUTH_EAST = 'se'
SOUTH = 's'
SOUTH_WEST = 'sw'
WEST = 'w'
NORTH_WEST = 'nw'
DIRECTIONS = {NORTH, NORTH_EAST, EAST, SOUTH_EAST, SOUTH, SOUTH_WEST, WEST, NORTH_WEST}


class _MeboMDNSListener:

    def remove_service(self, zeroconf, type, name):
        logging.debug("Service %s removed", name)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        logging.debug("Service %s added, service info: %s", name, info)


class ComponentFactory:
    """Factory class for generating classes of components"""

    @classmethod
    def _from_parent(cls, name, **actions):
        """Generates a class of the given type as a subclass of component

        :param name: Name of the generated class
        :type name: str
        :param actions: action names-> `callables`, which are closures using the parents shared request infrastructure
        :type actions: dict
        """
        cls = type(name, (Component,), actions)
        cls.__doc__ = f"""{name.upper()} Component"""
        return cls(actions=actions.keys())


class Component(ABC):
    """Abstract base class for all robot components"""

    def __init__(self, actions):
        self.actions = actions

    def __repr__(self):
        return '<{} actions={}>'.format(self.__class__, self.actions)


class Mebo:
    """Mebo represents a single physical robot"""

    # port used by mebo to broadcast its presence
    BROADCAST_PORT = 51110

    # port used to establish media (RTSP) sessions
    RTSP_PORT = 6667

    def __init__(self, ip=None, auto_connect=False):
        """Initializes a Mebo robot object and establishes an http connection

        If no ip or network is supplied, then we will autodiscover the mebo using mDNS.

        :param ip: IPv4 address of the robot as a string.
        :type ip: str
        :param auto_connect: if True, will autodiscover and connect at object creation time
        :type auto_connect: bool

        >>> m = Mebo()
        >>> m.connect()
        >>> m2 = Mebo(auto_connect=True)
        """
        self._session = Session()
        self._ip = None

        if ip:
            self.ip = ip
        elif auto_connect:
            self.connect()

        self._arm = None
        self._wrist = None
        self._claw = None
        self._speaker = None

        self._rtsp_session = None

    @property
    def endpoint(self):
        return 'http://{}'.format(self.ip)

    @property
    def ip(self):
        """The IP of the robot on the LAN

        This value is either provided explicitly at creation time or autodiscovered via mDNS
        """
        if self._ip is None:
            raise MeboConfigurationError('No configured or discovered value for ip address')
        return self._ip

    @ip.setter
    def ip(self, value):
        try:
            addr = IPv4Address(value)
            self._ip = addr
        except AddressValueError:
            raise MeboConfigurationError(f'Value {addr} set for IP is invalid IPv4 Address')

    @property
    def media(self):
        """an rtsp session representing the media streams (audio and video) for the robot"""
        if self._rtsp_session is None:
            url = f'rtsp://{self.ip}/streamhd/'
            self._rtsp_session = RTSPSession(
                url,
                port=self.RTSP_PORT,
                username='stream',
                realm='realm',
                user_agent='python-mebo'
            )
        return self._rtsp_session

    # TODO: rip this out, or change it to a hearbeat
    # listener which gets established, this has nothing to do with discovery
    # instead, use mDNS
    def _get_broadcast(self, address, timeout=10):
        """ Attempts to receive the UDP broadcast signal from Mebo
        on the supplied address. Raises an exception if no data is received
        before 'timeout' seconds.

        :param address: the broadcast address to bind
        :param timeout: how long the socket should wait without receiving data before raising socket.timeout

        :returns: A Broadcast object that containing the source IP, port, and data received.
        :raises: `socket.timeout` if no data is received before `timeout` seconds
        """
        logging.debug(f"reading from: {address}:{Mebo.BROADCAST_PORT}")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((address, Mebo.BROADCAST_PORT))
            s.settimeout(timeout)
            data, source = s.recvfrom(4096)
            logging.debug(f"Data received: {data}:{source}")
            return Broadcast(source[0], source[1], data)

    def _setup_video_stream(self):
        self._request(req='feedback_channel_init')
        self._request(req='set_video_gop', value=40)
        self._request(req='set_date', value=time.time())
        self._request(req='set_video_gop', value=40, speed=1)
        self._request(req='set_video_gop', value=40, speed=2)
        self._request(req='set_video_bitrate', value=600)
        self._request(req='set_video_bitrate', value=600, speed=1)
        self._request(req='set_video_bitrate', value=600, speed=2)
        self._request(req='set_resolution', value='720p')
        self._request(req='set_resolution', value='720p', speed=1)
        self._request(req='set_resolution', value='720p', speed=2)
        self._request(req='set_video_qp', value=42)
        self._request(req='set_video_qp', value=42, speed=1)
        self._request(req='set_video_qp', value=42, speed=2)
        self._request(req='set_video_framerate', value=20)
        self._request(req='set_video_framerate', value=20, speed=1)
        self._request(req='set_video_framerate', value=20, speed=2)

    def _get_stream(self, address, timeout=10):
        pass

    def _get_mdns(self, key="_camera._tcp.local."):
        try:
            zeroconf = Zeroconf()
            listener = _MeboMDNSListener()
            browser = ServiceBrowser(zeroconf, key, listener)
            time.sleep(1)
            for name, record in browser.services.items():
                info = zeroconf.get_service_info(record.key, record.alias)
                # note: the library we're using keeps these keys and values as bytes
                return info.properties[b'ip'].decode('ascii')
        finally:
            zeroconf.close()

    def _discover(self):
        """
        Runs the discovery scan to find Mebo on your LAN

        :returns: The IP address of the Mebo found on the LAN
        :raises: `MeboDiscoveryError` if discovery times out or the API probe produces a 40X or 50x status code
        """
        try:
            logging.debug('Looking for Mebo...')
            ip = self._get_mdns()
            return ip
        except socket.timeout:
            raise MeboDiscoveryError(('Unable to locate Mebo on the network.\n'
                                      '\tMake sure it is powered on and connected to LAN.\n'
                                      '\tIt may be necessary to power cycle the Mebo.'))

    def connect(self):
        """Connect to the mebo control server over HTTP

        If no IP exists for the robot already, the IP will be autodiscovered via mDNS. When there is already an IP, that will be used to make a canary request to get the command server software version. If the robot has been previously connected, no request is made at all.

        :raises: :class:`mebo.exceptions.MeboDiscoveryError` when a mDNS discovery fails
        :raises: :class:`mebo.exceptions.MeboConnectionError` when a TCP ConnectionError or HTTPError occurs
        """
        if self._ip is None:
            self.ip = self._discover()
            logging.debug(f'Mebo found at {self.ip}')
        try:
            version = self.version
            logging.debug(f'Mebo {version} connected')
        except (ConnectionError, HTTPError) as e:
            raise MeboConnectionError(f'Unable to connect to mebo: {e}')

    def _request(self, **params):
        """ private function to submit HTTP requests to Mebo's API

        :param params: arguments to pass as query params to the Mebo API. Might
        also include `need_response`, a kwarg dictating whether the caller
        requires the response object from the API.

        :returns: The `requests.HTTPResponse` object if `need_response` is True, `None` otherwise.
        """
        try:
            need_response = params.pop('need_response')
        except KeyError:
            # by default, don't return a response
            need_response = False
        try:
            response = self._session.get(self.endpoint, params=params)
            response.raise_for_status()
            if need_response:
                return response
        except (ConnectionError, HTTPError) as e:
            raise MeboRequestError(f'Request to Mebo failed: {e}')

    def visible_networks(self):
        """
        Retrieves list of wireless networks visible to Mebo.

        :returns: A dictionary of name to `WirelessNetwork`

        >>> m = Mebo(auto_connect=True)
        >>> print(m.visible_networks())
        """
        resp = self._request(req='get_rt_list', need_response=True)
        et = xmlfromstring(f'{resp.text}')
        visible = {}
        for nw in et.findall('w'):
            visible[nw.find('s').text.strip('"')] = WirelessNetwork(*(i.text.strip('"') for i in nw.getchildren()))
        return visible

    def add_router(self, auth_type, ssid, password, index=1):
        """
        Save a wireless network to the Mebo's list of routers
        """
        self._request(req='setup_wireless_save', auth=auth_type, ssid=ssid, key=password, index=index)

    def set_scan_timer(self, value=30):
        self._request(req='set_scan_timer', value=value)

    def restart(self):
        self._request(req='restart_system')

    def set_timer_state(self, value=0):
        self._request(req='set_timer_state', value=value)

    def get_wifi_cert(self):
        resp = self._request(req='get_wifi_cert', need_response=True)
        _, cert_type = resp.text.split(':')
        return cert_type.strip()

    def get_boundary_position(self):
        """ Gets boundary positions for 4 axes:

        Arm: s_up, s_down
        Claw: c_open, c_close
        Wrist Rotation: w_left & w_right
        Wrist Elevation: h_up, h_down

        :returns: dictionary of functions to boundary positions
        """
        resp = self._request(req='get_boundary_position', need_response=True)
        _, key_value_string = [s.strip() for s in resp.text.split(':')]
        return dict((k, int(v)) for k, v in [ks.strip().split('=') for ks in key_value_string.split('&')])

    @property
    def version(self):
        """returns the software version of the robot

        >>> m = Mebo(auto_connect=True)
        >>> m.version == '03.02.37'
        """
        if not hasattr(self, '_version') or self._version is None: 
            resp = self._request(req='get_version', need_response=True)
            _, version = resp.text.split(':')
            self._version = version.strip()
        return self._version

    def move(self, direction, speed=255, dur=1000):
        """Move the robot in a given direction at a speed for a given duration

        :param direction: map direction to move. 'n', 'ne', 'nw', etc.
        :param speed: a value in the range [0, 255]. default: 255
        :param dur: number of milliseconds the wheels should spin. default: 1000
        """
        directions = {
            NORTH: 'move_forward',
            NORTH_EAST: 'move_forward_right',
            EAST: 'move_right',
            SOUTH_EAST: 'move_backward_right',
            SOUTH: 'move_backward',
            SOUTH_WEST: 'move_backward_left',
            WEST: 'move_left',
            NORTH_WEST: 'move_forward_left'
        }
        direction = directions.get(direction.lower())
        if direction is None:
            raise MeboCommandError(
                'Direction must be one of the map directions: {}'.format(directions.keys()
            ))
        speed = min(speed, 255)
        # there is also a ts keyword that could be passed here.
        self._request(req=direction, dur=dur, value=speed)

    def turn(self, direction):
        """Turns a very small amount in the given direction

        :param direction: one of R or L
        """
        direction = direction.lower()[0]
        if direction not in {"r", "l"}:
            raise MeboCommandError('Direction for turn must be either "right", "left", "l", or "r"')
        call = 'inch_right' if direction == 'r' else 'inch_left'
        self._request(req=call)

    def stop(self):
        self._request(req='fb_stop')

    @property
    def claw(self):
        """ The claw component at the end of Mebo's arm

        >>> m = Mebo(auto_connect=True)
        >>> m.claw.open(dur=1000, **params)
        >>> m.claw.close(dur=400, **params)
        >>> m.claw.stop(**params)
        """
        if self._claw is None:
            claw = ComponentFactory._from_parent(
                'Claw',
                open=partial(self._request, req='c_open'),
                close=partial(self._request, req='c_close'),
                stop=partial(self._request, req='c_stop')
            )
            self._claw = claw
        return self._claw

    @property
    def wrist(self):
        """The wrist component of the robot

        The wrist component has the following actions:
        * rotate clockwise (to the right from the robot's perspective) OR counter-clockwise (to the left from the robot's perspective)
        * raise or lower

        >>> m = Mebo()
        >>> m.wrist.rotate_right(**params)
        >>> m.wrist.rotate_left(**params)
        >>> m.wrist.inch_right(**params)
        >>> m.wrist.inch_left(**params)
        >>> m.wrist.rotate_stop()
        >>> m.wrist.up()
        >>> m.wrist.down()
        >>> m.wrist.lift_stop()
        """
        if self._wrist is None:
            wrist = ComponentFactory._from_parent(
                'Wrist',
                rotate_right=partial(self._request, req='w_right'),
                inch_right=partial(self._request, req='inch_w_right'),
                rotate_left=partial(self._request, req='w_left'),
                inch_left=partial(self._request, req='inch_w_left'),
                rotate_stop=partial(self._request, req='w_stop'),
                up=partial(self._request, req='h_up'),
                down=partial(self._request, req='h_down'),
                lift_stop=partial(self._request, req='h_stop'),
            )
            self._wrist = wrist
        return self._wrist

    @property
    def arm(self):
        """The arm component of mebo

        >>> m = Mebo(auto_connect=True)
        >>> m.arm.up(dur=1000, **params)
        >>> m.arm.down(dur=1000, **params)
        >>> m.arm.stop(**params)
        """
        up = partial(self._request, req='s_up')
        up.__doc__ = """Move the arm up

        :param dur: The duration of the arm movement
        :type dur: int
        """
        down = partial(self._request, req='s_down')
        down.__doc__ = """Move the arm down

        :param dur: The duration of the arm movement
        :type dur: int
        """
        stop = partial(self._request, req='s_stop')
        stop.__doc__ = """Stop the arm"""

        if self._arm is None:
            arm = ComponentFactory._from_parent(
                'Arm',
                up=up,
                down=down,
                stop=stop
            )
            self._arm = arm
        return self._arm

    @property
    def speaker(self):
        """
        >>> m = Mebo(auto_connect=True)
        >>> m.speaker.set_volume(value=6)
        >>> m.speaker.get_volume()
        >>> m.speaker.play_sound(**params)
        """
        if self._speaker is None:
            speaker = ComponentFactory._from_parent(
                'Speaker',
                set_volume=partial(self._request, req='set_spk_volume'),
                play_sound=partial(self._request, req='audio_out0'))
            self._speaker = speaker
        return self._speaker
