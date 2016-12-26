import requests
from .exceptions import (
    MeboDiscoveryError,
    MeboRequestError,
)


# class MetaComponent(type):
#
#     def __new__(cls, name, parent):
#         self.name = name


class Component():

    @classmethod
    def from_parent(cls, name, parent, **actions):
        self = cls(name, parent, **actions)
        for name, action in actions.iteritems():
            setattr(self, name, action)


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
        self._request('setup_wireless_save', auth=auth_type, ssid=ssid, key=password, index=index)

    def set_scan_timer(self, value=30):
        self._request('set_scan_timer', value=value)

    def restart(self):
        self._request('restart_system')

    def set_timer_state(self, value=0):
        self._request('set_timer_state', value=value)

    def get_wifi_cert(self):
        resp = self._request('get_wifi_cert')
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
        return Component.from_parent('Claw', self)

    @property
    def wrist(self):
        """
        Usage: mebo.Mebo().wrist.clockwise(**params)
        Usage: mebo.Mebo().wrist.counter_clockwise(**params)
        Usage: mebo.Mebo().wrist.position
        """
        return Component.from_parent('Wrist', self)

    @property
    def arm(self):
        """
        Usage: mebo.Mebo().arm.raise(**params)
        Usage: mebo.Mebo().arm.lower(**params)
        Usage: mebo.Mebo().arm.position
        """
        return Component.from_parent('Arm', self)
