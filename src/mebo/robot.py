"""Classes and methods for working with the physical Mebo robot"""

import logging
import os
import sys
import time
from abc import ABC
from collections import namedtuple
from functools import partial
from ipaddress import AddressValueError, IPv4Address

from xml.etree.ElementTree import fromstring as xmlfromstring

from requests import Session
from requests.exceptions import ConnectionError, HTTPError

from zeroconf import ServiceBrowser, Zeroconf, IPVersion

from .exceptions import (
    MeboCommandError,
    MeboDiscoveryError,
    MeboRequestError,
    MeboConnectionError,
    MeboConfigurationError,
)

from mebo.stream.session import (
    RTSPSession,
)


# TODO: set up better logging
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=LOGLEVEL)

Broadcast = namedtuple("Broadcast", ["ip", "port", "data"])
WirelessNetwork = namedtuple(
    "WirelessNetwork", ["ssid", "mac", "auth", "q", "si", "nl", "channel"]
)

NORTH = "n"
NORTH_EAST = "ne"
EAST = "e"
SOUTH_EAST = "se"
SOUTH = "s"
SOUTH_WEST = "sw"
WEST = "w"
NORTH_WEST = "nw"
DIRECTIONS = [NORTH, NORTH_EAST, EAST, SOUTH_EAST, SOUTH, SOUTH_WEST, WEST, NORTH_WEST]


class ComponentFactory:
    """Factory class for generating classes of components"""

    @classmethod
    def build(cls, name, **actions):
        """Generates a class of the given type as a subclass of component

        :param name: Name of the generated class
        :type name: str
        :param actions: action names-> `callables`, which are closures using the parents shared request infrastructure
        :type actions: dict
        """
        cls = type(name, (Component,), actions)
        cls.__doc__ = f"""Mebo {name.upper()} Component"""
        return cls(actions=actions.keys())


class Component(ABC):
    """Abstract base class for all robot components"""

    def __init__(self, actions):
        self.actions = actions

    def __repr__(self):
        return "<{} actions={}>".format(self.__class__, self.actions)


class Mebo:
    """Mebo represents a single physical robot"""

    # port used to establish media (RTSP) sessions
    RTSP_PORT = 6667

    def __init__(self, ip=None, autoconnect=True):
        """Initializes a Mebo robot object and establishes an http connection to the robot

        If `autoconnect` is True (default), then we will autodiscover the robot using mDNS.
        Alternatively, if autoconnect is False and `ip` is set to a valid IPV4Address, we will attempt to connect using that IP.
        If `ip` is not a valid IPv4 Address and autoconnect is False, it is error.

        :param ip: IPv4 address of the robot as a string.
        :type ip: str
        :param autoconnect: if True, will autodiscover and connect at object creation time
        :type autoconnect: bool

        >>> m = Mebo()
        >>> assert m.is_connected
        """
        # TODO: I don't think the HTTP server on Mebo supports long lived connections
        # so we're not really getting anything from this. Maybe just use `request.get` instead?
        self._session = Session()
        self._ip = None
        self._mac = None
        # all mebos use this as their mDNS domain. Typically the robot
        # will be named Camera-{mac_address}._camer._tcp.local"
        self._mdns_domain = "_camera._tcp.local."
        self._mdns_name = None

        self._move_directions = None

        if autoconnect:
            self._discover_via_mdns()
        else:
            self.ip = ip

        self._arm = None
        self._wrist = None
        self._claw = None
        self._speaker = None

        self._rtsp_session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._session.close()

    @property
    def ip(self) -> IPv4Address:
        """The IPv4Address of the robot on the LAN

        This value is either provided explicitly at creation time or autodiscovered via mDNS.
        A valid Mebo object always has this property
        """
        if self._ip is None:
            raise MeboConfigurationError(
                "No configured or discovered value for ip address"
            )
        return self._ip

    @ip.setter
    def ip(self, value):
        try:
            addr = IPv4Address(value)
            self._ip = addr
        except AddressValueError:
            raise MeboConfigurationError(f"{value} is not a valid IPv4Address")

    @property
    def mdns_name(self):
        """If Mebo is disocered through mDNS, the .local hostname of the robot.
        None otherwise"""
        return self._mdns_name

    @mdns_name.setter
    def mdns_name(self, name):
        if name.endswith(self._mdns_domain):
            self._mdns_name = name
        else:
            raise MeboConfigurationError(
                f"Local domain name ({name}) should end in {self._mdns_domain}"
            )

    @property
    def endpoint(self):
        """HTTP Endpoint serving the Mebo control API"""
        return f"http://{self.ip}"

    @property
    def is_connected(self):
        """
        True if the self.ip is a valid IPv4Address and it's possible to grab the version via HTTP.
        False otherwise, including in the case of an HTTP or connection Error

        :raises: :class:`mebo.exceptions.MeboDiscoveryError` when a mDNS discovery fails
        :raises: :class:`mebo.exceptions.MeboConnectionError` when a TCP ConnectionError or HTTPError occurs
        """
        logging.debug(f"Connecting to Mebo at {self.ip}")
        try:
            return self.ip and self.version is not None
        except (ConnectionError, HTTPError, MeboConfigurationError) as e:
            raise MeboConnectionError(f"Error connecting to Mebo: {e}")

    @property
    def media(self):
        """an rtsp session representing the media streams (audio and video) for the robot"""
        if self._rtsp_session is None:
            url = f"rtsp://{self.ip}/streamhd/"
            self._rtsp_session = RTSPSession(
                url,
                port=self.RTSP_PORT,
                username="stream",
                realm="realm",
                user_agent="python-mebo",
            )
        return self._rtsp_session

    def _setup_video_stream(self):
        self._request(req="feedback_channel_init")
        self._request(req="set_video_gop", value=40)
        self._request(req="set_date", value=time.time())
        self._request(req="set_video_gop", value=40, speed=1)
        self._request(req="set_video_gop", value=40, speed=2)
        self._request(req="set_video_bitrate", value=600)
        self._request(req="set_video_bitrate", value=600, speed=1)
        self._request(req="set_video_bitrate", value=600, speed=2)
        self._request(req="set_resolution", value="720p")
        self._request(req="set_resolution", value="720p", speed=1)
        self._request(req="set_resolution", value="720p", speed=2)
        self._request(req="set_video_qp", value=42)
        self._request(req="set_video_qp", value=42, speed=1)
        self._request(req="set_video_qp", value=42, speed=2)
        self._request(req="set_video_framerate", value=20)
        self._request(req="set_video_framerate", value=20, speed=1)
        self._request(req="set_video_framerate", value=20, speed=2)

    def _get_stream(self, address, timeout=10):
        pass

    def _add_service(self, zeroconf, service_type, state_change, name):
        # TODO: this is a problem with multiple robots on the network because
        # it kills the connection
        info = zeroconf.get_service_info(service_type, name)
        logging.debug(
            "(%s): %s found at %s", state_change, name, info.parsed_addresses()
        )
        if name.endswith(self._mdns_domain):
            service_props = {
                k.decode("ascii"): v.decode("ascii") for k, v in info.properties.items()
            }
            self._mac = ":".join(
                "".join(p)
                for p in zip(service_props["mac"][::2], service_props["mac"][1::2])
            )
            self.ip = service_props["ip"]
            self.mdns_name = name
        else:
            logging.debug(f"Igoring service {name}")

    def _discover_via_mdns(self, timeout=3, tick=0.1):
        """
        Runs the discovery scan to find Mebo on your LAN

        :returns: The IP address of the Mebo found on the LAN
        :raises: `MeboDiscoveryError` if discovery times out or the API probe produces a 40X or 50x status code
        """
        try:
            # Only care about IPV4
            zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            start = time.time()
            logging.debug("Starting search for Mebo...")
            with ServiceBrowser(
                zeroconf, self._mdns_domain, handlers=[self._add_service]
            ):
                while self._ip is None and time.time() - start < timeout:
                    logging.debug("Still Looking for Mebo...")
                    time.sleep(tick)
            assert self._ip is not None
            logging.debug(
                "Mebo(mac:%s) is at (%s)->(%s)", self._mac, self._mdns_name, self._ip
            )
        except AssertionError:
            raise MeboDiscoveryError(
                (
                    "Unable to locate Mebo on the network.\n"
                    "\tMake sure it is powered on and connected to LAN.\n"
                    "\tIt may be necessary to power cycle the Mebo."
                )
            )
        finally:
            if zeroconf.started:
                zeroconf.close()

    def _request(self, **params):
        """private function to submit HTTP requests to Mebo's API

        :param params: arguments to pass as query params to the Mebo API

        :returns: The `requests.HTTPResponse`
        """
        try:
            response = self._session.get(self.endpoint, params=params)
            response.raise_for_status()
            return response
        except (ConnectionError, HTTPError) as e:
            raise MeboRequestError(f"Request to Mebo failed: {e}")

    def visible_networks(self):
        """
        Retrieves list of wireless networks visible to Mebo.

        :returns: A dictionary of name to `WirelessNetwork`

        >>> m = Mebo()
        >>> print(m.visible_networks())
        """
        resp = self._request(req="get_rt_list")
        et = xmlfromstring(f"{resp.text}")
        visible = {}
        for nw in et.findall("w"):
            wlan = WirelessNetwork(*(i.text.strip('"') for i in nw))
            visible[wlan.ssid] = wlan
        return visible

    def add_router(self, auth_type, ssid, password, index=1):
        """
        Save a wireless network to the Mebo's list of routers

        Note that the parameters are passed to the robot as query params, completely in the clear.
        Take caution if you are on an untrusted network.
        """
        self._request(
            req="setup_wireless_save",
            auth=auth_type,
            ssid=ssid,
            key=password,
            index=index,
        )

    def set_scan_timer(self, value=30):
        self._request(req="set_scan_timer", value=value)

    def restart(self):
        """Restarts the Mebo"""
        self._request(req="restart_system")

    def set_timer_state(self, value=0):
        self._request(req="set_timer_state", value=value)

    def get_wifi_cert(self):
        resp = self._request(req="get_wifi_cert")
        _, cert_type = resp.text.split(":")
        return cert_type.strip()

    def get_boundary_position(self):
        """Gets boundary positions for 4 axes:

        Arm: s_up, s_down
        Claw: c_open, c_close
        Wrist Rotation: w_left & w_right
        Wrist Elevation: h_up, h_down

        :returns: dictionary of functions to boundary positions

        >>> m = Mebo()
        >>> m.get_boundary_position()
        """
        resp = self._request(req="get_boundary_position")
        _, key_value_string = [s.strip() for s in resp.text.split(":")]
        return dict(
            (k, int(v))
            for k, v in [ks.strip().split("=") for ks in key_value_string.split("&")]
        )

    @property
    def version(self):
        """returns the software version of the robot

        >>> m = Mebo()
        >>> m.version == '03.02.37'
        """
        try:
            resp = self._request(req="get_version")
            _, version = resp.text.split(":")
            return version.strip()
        except MeboRequestError as e:
            logging.debug(f"Error requesting model: {e}")
            return None

    @property
    def model(self):
        """returns the robot model. For this version, always 
        expected to be `001`
        >>> m = Mebo()
        >>> m.model == '001'
        """
        try:
            resp = self._request(req="get_model")
            _, model = resp.text.split(":")
            return model.strip()
        except MeboRequestError as e:
            logging.debug(f"Error requesting model: {e}")
            return None

    @property
    def move_directions(self):
        if self._move_directions is None:
            self._move_directions = dict(
                zip(
                    DIRECTIONS,
                    [
                        "move_forward",
                        "move_forward_right",
                        "move_right",
                        "move_backward_right",
                        "move_backward",
                        "move_backward_left",
                        "move_left",
                        "move_forward_left",
                    ],
                )
            )
        return self._move_directions

    def move(self, direction, speed=255, dur=1000):
        """Move the robot in a given direction at a speed for a given duration

        :param direction: one of eight cardinal directions, from the perspective of the robot: \
            'n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'.
        :param speed: a value in the range [0, 255]. default: 255
        :param dur: number of milliseconds the wheels should spin. default: 1000
        """
        direction = self.move_directions.get(direction.lower())
        if direction is None:
            raise MeboCommandError(
                "Direction must be one of the map directions: {}".format(
                    self.move_directions.keys()
                )
            )
        speed = min(speed, 255)
        # there is also a ts keyword that could be passed here.
        self._request(req=direction, dur=dur, value=speed)

    def turn(self, direction):
        """Turns a very small amount in the given direction

        :param direction: one of R or L
        """
        direction = direction.lower()[0]
        if direction not in {"r", "l"}:
            raise MeboCommandError(
                'Direction for turn must be either "right", "left", "l", or "r"'
            )
        call = "inch_right" if direction == "r" else "inch_left"
        self._request(req=call)

    def stop(self):
        self._request(req="fb_stop")

    @property
    def claw(self):
        """The claw component at the end of Mebo's arm

        >>> m = Mebo()
        >>> m.claw.open(dur=1000, **params)
        >>> m.claw.close(dur=400, **params)
        >>> m.claw.stop(**params)
        """
        if self._claw is None:
            claw = ComponentFactory.build(
                "Claw",
                open=partial(self._request, req="c_open"),
                close=partial(self._request, req="c_close"),
                stop=partial(self._request, req="c_stop"),
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
            wrist = ComponentFactory.build(
                "Wrist",
                rotate_right=partial(self._request, req="w_right"),
                inch_right=partial(self._request, req="inch_w_right"),
                rotate_left=partial(self._request, req="w_left"),
                inch_left=partial(self._request, req="inch_w_left"),
                rotate_stop=partial(self._request, req="w_stop"),
                up=partial(self._request, req="h_up"),
                down=partial(self._request, req="h_down"),
                lift_stop=partial(self._request, req="h_stop"),
            )
            self._wrist = wrist
        return self._wrist

    @property
    def arm(self):
        """The arm component of mebo

        >>> m = Mebo()
        >>> m.arm.up(dur=1000, **params)
        >>> m.arm.down(dur=1000, **params)
        >>> m.arm.stop(**params)
        """
        up = partial(self._request, req="s_up")
        up.__doc__ = """Move the arm up

        :param dur: The duration of the arm movement
        :type dur: int
        """
        down = partial(self._request, req="s_down")
        down.__doc__ = """Move the arm down

        :param dur: The duration of the arm movement
        :type dur: int
        """
        stop = partial(self._request, req="s_stop")
        stop.__doc__ = """Stop the arm"""

        if self._arm is None:
            arm = ComponentFactory.build("Arm", up=up, down=down, stop=stop)
            self._arm = arm
        return self._arm

    @property
    def speaker(self):
        """
        >>> m = Mebo()
        >>> m.speaker.set_volume(value=6)
        >>> m.speaker.get_volume()
        >>> m.speaker.play_sound(**params)
        """
        set_volume = partial(self._request, req="set_spk_volume")
        set_volume.__doc__ = """Set the volume of the speaker

        The value passed in to set the volume must be in the range [0, 100]
        """
        play_sound = partial(self._request, req="audio_out0")
        # TODO: how do you change what noise is played?
        play_sound.__doc__ = """Play one of the stored sounds

        through the speaker. 
        """
        if self._speaker is None:
            speaker = ComponentFactory.build(
                "Speaker", set_volume=set_volume, play_sound=play_sound
            )
            self._speaker = speaker
        return self._speaker
