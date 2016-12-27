import functools
import requests
from .exceptions import (
    MeboDiscoveryError,
    MeboRequestError,
)


class Component:

    @classmethod
    def from_parent(cls, name):
        cls.__name__ = name
        return cls()


class Mebo(object):
    """ The main mebo class that represents a single robot.
    """

    def __init__(self, ip=None):
        self._session = requests.Session()
        if ip is None:
            self._discover()
        else:
            self.ip = ip
        self._version = None
        self._arm = None
        self._wrist = None
        self._claw = None

    def _discover(self):
        """
        Runs the discovery scan to find Mebo on your LAN
        """

        try:
            print("Scanning for mebo...")
            # get IP address
            # scan netmask a la nmap, do "get_version" for that IP
            # try get_version, set_timer_state, get_wifi_cert
            # break
        except Exception:
            raise MeboDiscoveryError('Unable to locate Mebo on the network?')

    def _request(self, **params):
        try:
            response = self._session.get('http://{}'.format(self.ip), params=params)
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

    def move(self, velocity, duration):
        """
        :param velocity: a value in the range [-255, 255]. Sign controls direction.
        :param duration: number of milliseconds to move the robot
        """
        direction = 'move_forward' if velocity >= 0 else 'move_backward'
        velocity = abs(velocity)
        # there is also a ts keyword that could be passed here.
        self._request(req=direction, dur=duration, value=velocity)

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
            claw = Component.from_parent('Claw')
            claw.open = functools.partial(self._request, req='c_open')
            claw.close = functools.partial(self._request, req='c_close')
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
            wrist = Component.from_parent('Wrist')
            wrist.clockwise = functools.partial(self._request, req='w_right')
            wrist.counter_clockwise = functools.partial(self._request, req='w_left')
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
            arm = Component.from_parent('Arm')
            arm.up = functools.partial(self._request, req='s_up')
            arm.down = functools.partial(self._request, req='s_down')
            self._arm = arm
        return self._arm
