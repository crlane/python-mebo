import socket

from collections import namedtuple
from functools import partial
from ipaddress import IPv4Network
from requests import Session
from requests.exceptions import (
    ConnectionError,
    HTTPError
)

from .exceptions import (
    MeboCommandError,
    MeboDiscoveryError,
    MeboRequestError,
    MeboConfigurationError
)

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

    def __init__(self, ip=None, broadcast=None, network=None):
        """ Initializes a Mebo robot object

        :param ip: IPv4 address of the robot as a string
        :param network: IPv4 subnet in cidr block notation as a string. Ex: '192.168.1.0/24'
        """
        self._session = Session()
        self._network = None
        self._ip = None

        if ip:
            self._ip = ip
        elif ip is None and network:
            self._ip = self._discover(network)
        else:
            raise MeboConfigurationError('Must supply either an ip or subnet to find mebo')

        self._endpoint = 'http://{}'.format(self._ip)
        self._version = None
        self._arm = None
        self._wrist = None
        self._claw = None
        self._speaker = None

    def _probe(self, ip):
        """ Checks the given IPv4 address for Mebo HTTP API functionality.

        :param ip: The ip address to probe for the mebo API
        :returns: The response object from the HTTP request
        """
        return self._session.get('http://{}/get_version'.format(ip))

    def _get_broadcast(self, address='', timeout=10):
        """ Attempts to receive the UDP broadcast signal from Mebo
        on the supplied address. Raises an exception if no data is received
        before 'timeout' seconds.

        :param address: the broadcast address to bind
        :param timeout: how long the socket should wait without receiving data before raising socket.timeout

        :returns: A Broadcast object that containing the source IP, port, and data received.
        :raises: `socket.timeout` if no data is received before `timeout` seconds
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((address, Mebo.BROADCAST_PORT))
            s.settimeout(timeout)
            data, source = s.recvfrom(4096)
            return Broadcast(source[0], source[1], data)

    def _discover(self, network):
        """
        Runs the discovery scan to find Mebo on your LAN

        :param network: The IPv4 network netmask as a CIDR string. Example: 192.168.1.0/24
        :returns: The IP address of the Mebo found on the LAN
        :raises: `MeboDiscoveryError` if broadcast discovery times out or the API probe produces a 40X or 50x status code
        """
        try:
            print('Looking for Mebo...')
            self._network = IPv4Network(network)
            addr = self._network.broadcast_address.compressed
            broadcast = self._get_broadcast(addr)
            api_response = self._probe(broadcast.ip)
            api_response.raise_for_status()
            return broadcast.ip
        except (socket.timeout, HTTPError):
            raise MeboDiscoveryError('Unable to locate Mebo on the network. Make sure it is powered and connected to LAN')

    def _request(self, **params):
        try:
            response = self._session.get(self._endpoint, params=params)
            response.raise_for_status()
            return response
        except (ConnectionError, HTTPError) as e:
            raise MeboRequestError('Request to Mebo failed: {}'.format(str(e)))

    def router_list(self):
        resp = self._request('get_rt_list')
        return resp.text

    def add_router(self, auth_type, ssid, password, index=1):
        self._request(req='setup_wireless_save', auth=auth_type, ssid=ssid, key=password, index=index)

    def set_scan_timer(self, value=30):
        self._request(req='set_scan_timer', value=value)

    def restart(self):
        self._request(req='restart_system')

    def set_timer_state(self, value=0):
        self._request(req='set_timer_state', value=value)

    def get_wifi_cert(self):
        resp = self._request(req='get_wifi_cert')
        _, cert_type = resp.text.split(':')
        return cert_type.strip()

    def get_boundary_position(self):
        resp = self._request(req='get_boundary_position')
        return resp

    @property
    def version(self):
        if not self._version:
            resp = self._request(req='get_version')
            _, version = resp.text.split(':')
            self._version = version.strip()
        return self._version

    def move(self, direction, speed, duration):
        """
        :param direction: map direction to move. 'n', 'ne', 'nw'
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
        Usage: mebo.Mebo().wrist.clockwise(**params)
        Usage: mebo.Mebo().wrist.counter_clockwise(**params)
        """
        if self._wrist is None:
            wrist = Component.from_parent(
                'Wrist',
                rotate_right=partial(self._request, req='w_right'),
                inch_right=partial(self._request, req='inch_w_right'),
                rotate_left=partial(self._request, req='w_left'),
                inch_left=partial(self._request, req='inch_w_left'),
                stop=partial(self._request, req='w_stop'),
                up=partial(self._request, req='h_up'),
                down=partial(self._request, req='h_down'),
                stop_=partial(self._request, req='h_stop'),
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
