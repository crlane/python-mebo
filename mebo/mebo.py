from requests import Session
from functools import partial

from .exceptions import (
    MeboCommandError,
    MeboDiscoveryError,
    MeboRequestError,
)

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
    """ The main mebo class that represents a single robot.
    """

    def __init__(self, ip=None):
        self._session = Session()
        if ip is None:
            self._discover()
        else:
            self.ip = ip
        self._endpoint = 'http://{}'.format(self.ip)
        self._version = None
        self._arm = None
        self._wrist = None
        self._claw = None
        self._speaker = None

    def _discover(self):
        """
        Runs the discovery scan to find Mebo on your LAN
        """

        try:
            print("Scanning for mebo...")
            # The mebo client on iOS appears to do something like this:
            # 1. get IP address of machine
            # 2. scan netmask a la nmap, do "get_version" for that IP
            # 3. try get_version, set_timer_state, get_wifi_cert
            # break
        except Exception:
            raise MeboDiscoveryError('Unable to locate Mebo on the network?')

    def _request(self, **params):
        try:
            response = self._session.get(self._endpoint, params=params)
            response.raise_for_status()
            return response
        except Exception as e:
            raise MeboRequestError('Request to Mebo failed: {}'.format(e.message))

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

    @property
    def version(self):
        if not self._version:
            resp = self._request(req='get_version')
            _, version = resp.text.split(':')
            self._version = version.strip()
        return self._version

    def move(self, direction, velocity, duration):
        """
        :param direction: map direction to move. 'n', 'ne', 'nw'
        :param velocity: a value in the range [0, 255].
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
        velocity = min(velocity, 255)
        # there is also a ts keyword that could be passed here.
        self._request(req=direction, dur=duration, value=velocity)

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
        Usage: mebo.Mebo().claw.position
        """
        if self._claw is None:
            claw = Component.from_parent('Claw',
                open=partial(self._request, req='c_open'),
                close=partial(self._request, req='c_close')
            )
            self._claw = claw
        return self._claw

    @property
    def wrist(self):
        """
        Usage: mebo.Mebo().wrist.clockwise(**params)
        Usage: mebo.Mebo().wrist.counter_clockwise(**params)
        Usage: mebo.Mebo().wrist.position
        """
        if self._wrist is None:
            wrist = Component.from_parent('Wrist',
                cw=partial(self._request, req='w_right'),
                fine_cw=partial(self._request, req='inch_w_right'),
                ccw=partial(self._request, req='w_left'),
                fine_ccw=partial(self._request, req='inch_w_left'),
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
        Usage: mebo.Mebo().arm.position
        """
        if self._arm is None:
            arm = Component.from_parent('Arm',
                up=partial(self._request, req='s_up'),
                down=partial(self._request, req='s_down'),
                stop=partial(self._request, req='s_stop'),
            )
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
            speaker = Component.from_parent('Speaker',
                set_volume=partial(self._request, req='set_spk_volume'),
                play_sound=partial(self._request, req='audio_out0'))
            self._speaker = speaker
        return self._speaker
