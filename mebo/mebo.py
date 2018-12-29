import logging
import socket
import time

from collections import namedtuple
from functools import partial
from ipaddress import IPv4Network

import netifaces

from requests import Session
from requests.exceptions import (
    ConnectionError,
    HTTPError
)

from zeroconf import ServiceBrowser, Zeroconf

class MeboMDNSListener:

    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        print("Service %s added, service info: %s" % (name, info))


from .exceptions import (
    MeboCommandError,
    MeboDiscoveryError,
    MeboRequestError,
    MeboConfigurationError
)

from mebo.stream.session import (
    RTSPSession,
)


logging.getLogger(__name__)

Broadcast = namedtuple('Broadcast', ['ip', 'port', 'data'])

NORTH = 'n'
NORTH_EAST = 'ne'
EAST = 'e'
SOUTH_EAST = 'se'
SOUTH = 's'
SOUTH_WEST = 'sw'
WEST = 'w'
NORTH_WEST = 'nw'


class Component:
    """ Factory class for generating classes of components
    """

    @classmethod
    def from_parent(cls, name, **actions):
        """ Generates a class of the given type as a subclass of component
        :param name: Name of the generated class
        :param actions: A dictionary of action names->callables (closures from parent)
        """
        cls = type(name, (Component,), actions)
        return cls(actions=actions.keys())

    def __init__(self, actions):
        self.actions = actions

    def __repr__(self):
        return '<{} actions={}>'.format(self.__class__, self.actions)


class Mebo(object):
    """ The main mebo class that represents a single robot
    """

    # port used by mebo to broadcast its presence
    BROADCAST_PORT = 51110

    # port used to establish media (RTSP) sessions
    RTSP_PORT = 6667

    def __init__(self, ip=None, broadcast=None, network=None):
        """ Initializes a Mebo robot object

        :param ip: IPv4 address of the robot as a string
        :param network: IPv4 subnet in cidr block notation as a string. Ex: '192.168.1.0/24'
        """
        self._session = Session()
        self._ip = None

        if ip:
            self._ip = ip
        else:
            try:
                self._ip = self._discover()
            except Exception as e:
                raise MeboConfigurationError(
                    f'Unable to autodiscover mebo ip from mDNS, please enter ip or network info. {e}'
                )

        self._endpoint = 'http://{}'.format(self._ip)
        self._version = None
        self._arm = None
        self._wrist = None
        self._claw = None
        self._speaker = None

        self._rtsp_session = None

    @property
    def ip(self):
        return self._ip

    @property
    def media(self):
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

    def _probe(self, ip):
        """ Checks the given IPv4 address for Mebo HTTP API functionality.

        :param ip: The ip address to probe for the mebo API
        :returns: The response object from the HTTP request
        """
        return self._session.get('http://{}/?req=get_version'.format(ip))

    # TODO: rip this out, or change it to a hearbeat
    # listener which gets established, this has nothing to do with discovery
    # instead, use mdn
    def _get_broadcast(self, address, timeout=10):
        """ Attempts to receive the UDP broadcast signal from Mebo
        on the supplied address. Raises an exception if no data is received
        before 'timeout' seconds.

        :param address: the broadcast address to bind
        :param timeout: how long the socket should wait without receiving data before raising socket.timeout

        :returns: A Broadcast object that containing the source IP, port, and data received.
        :raises: `socket.timeout` if no data is received before `timeout` seconds
        """
        print(f"reading from: {address}:{Mebo.BROADCAST_PORT}")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((address, Mebo.BROADCAST_PORT))
            s.settimeout(timeout)
            data, source = s.recvfrom(4096)
            print(f"Data received: {data}:{source}")
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
            listener = MeboMDNSListener()
            browser = ServiceBrowser(zeroconf, key, listener)
            time.sleep(1)
            for name, record in browser.services.items():
                info = zeroconf.get_service_info(record.key, record.alias)
                return info.properties[b'ip'].decode('ascii')
        finally:
            zeroconf.close()

    def _discover(self):
        """
        Runs the discovery scan to find Mebo on your LAN

        :param network: The IPv4 network netmask as a CIDR string. Example: 192.168.1.0/24
        :returns: The IP address of the Mebo found on the LAN
        :raises: `MeboDiscoveryError` if broadcast discovery times out or the API probe produces a 40X or 50x status code
        """
        try:
            print('Looking for Mebo...')
            ip = self._get_mdns()
            api_response = self._probe(ip)
            api_response.raise_for_status()
            print('Mebo found at {}'.format(ip))
            return ip
        except (socket.timeout, HTTPError):
            raise MeboDiscoveryError(('Unable to locate Mebo on the network.\n'
                                      '\tMake sure it is powered on and connected to LAN.\n'
                                      '\tIt may be necessary to power cycle the Mebo.'))

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
            response = self._session.get(self._endpoint, params=params)
            response.raise_for_status()
            if need_response:
                return response
        except (ConnectionError, HTTPError) as e:
            raise MeboRequestError('Request to Mebo failed: {}'.format(str(e)))

    def visible_networks(self):
        """ Retrives list of wireless networks visible to Mebo.

        :returns: A string of XML containing the currently available wireless networks
        """
        resp = self._request(req='get_rt_list', need_response=True)
        return resp.text

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
        if not self._version:
            resp = self._request(req='get_version', need_response=True)
            _, version = resp.text.split(':')
            self._version = version.strip()
        return self._version

    def move(self, direction, speed, duration):
        """
        :param direction: map direction to move. 'n', 'ne', 'nw', etc.
        :param speed: a value in the range [0, 255].
        :param duration: number of milliseconds the wheels should spin
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
            raise MeboCommandError('Direction must be one of the map directions: {}'.format(directions.keys()))
        speed = min(speed, 255)
        # there is also a ts keyword that could be passed here.
        self._request(req=direction, dur=duration, value=speed)

    def turn(self, direction):
        """ Turns a very small amount in the given direction
        """
        if direction not in ('right', 'left'):
            raise MeboCommandError('Direction for turn must be either "right" or "left"')
        call = 'inch_right' if direction == 'right' else 'inch_left'
        self._request(req=call)

    def stop(self):
        self._request(req='fb_stop')

    @property
    def claw(self):
        """
        Usage: mebo.Mebo().claw.open(**params)
        Usage: mebo.Mebo().claw.close(**params)
        Usage: mebo.Mebo().claw.stop(**params)
        """
        if self._claw is None:
            claw = Component.from_parent(
                'Claw',
                open=partial(self._request, req='c_open'),
                close=partial(self._request, req='c_close'),
                stop=partial(self._request, req='c_stop')
            )
            self._claw = claw
        return self._claw

    @property
    def wrist(self):
        """
        Usage: Mebo().wrist.rotate_right(**params)
        Usage: Mebo().wrist.rotate_left(**params)
        Usage: Mebo().wrist.inch_right(**params)
        Usage: Mebo().wrist.inch_left(**params)
        Usage: Mebo().wrist.rotate_stop()
        Usage: Mebo().wrist.up()
        Usage: Mebo().wrist.down()
        Usage: Mebo().wrist.lift_stop()
        """
        if self._wrist is None:
            wrist = Component.from_parent(
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
        """
        Usage: mebo.Mebo().arm.up(**params)
        Usage: mebo.Mebo().arm.down(**params)
        Usage: mebo.Mebo().arm.stop(**params)
        """
        if self._arm is None:
            arm = Component.from_parent(
                'Arm',
                up=partial(self._request, req='s_up'),
                down=partial(self._request, req='s_down'),
                stop=partial(self._request, req='s_stop'))
            self._arm = arm
        return self._arm

    @property
    def speaker(self):
        """
        Usage: mebo.Mebo().speaker.set_volume(value=6)
        Usage: mebo.Mebo().speaker.get_volume()
        Usage: mebo.Mebo().speaker.play_sound(**params)
        """
        if self._speaker is None:
            speaker = Component.from_parent(
                'Speaker',
                set_volume=partial(self._request, req='set_spk_volume'),
                play_sound=partial(self._request, req='audio_out0'))
            self._speaker = speaker
        return self._speaker
