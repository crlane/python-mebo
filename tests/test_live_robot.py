"""To run these tests: `py.test -m 'live_robot'`

They are written for my personal Mebo, so YMMV if you have a different version
"""
import os
import time

import pytest

from mebo import Mebo
from mebo.robot import DIRECTIONS


os.environ['LOGLEVEL'] = 'debug'


@pytest.fixture(scope='session')
def live_robot():
    return Mebo()

@pytest.mark.live_robot
def test_is_connected(live_robot):
    assert live_robot.is_connected

@pytest.mark.live_robot
def test_get_version(live_robot):
    assert live_robot.version == '03.02.37'

@pytest.mark.live_robot
def test_get_networks(live_robot):
    assert live_robot.visible_networks()

@pytest.mark.live_robot
@pytest.mark.motion
@pytest.mark.parametrize('direction', DIRECTIONS)
def test_live_robot_movement(live_robot, direction):
    live_robot.move(direction)
    time.sleep(1.0)
    assert True

@pytest.mark.live_robot
@pytest.mark.components
@pytest.mark.parametrize('component', [
    'arm',
    'wrist',
    'claw',
])
def test_component_motion(live_robot, component):
    c = getattr(live_robot, component)
    for act in c.actions:
        getattr(c, act)()
        time.sleep(1.0)


@pytest.mark.media
@pytest.mark.live_robot
def test_live_stream_capture(live_robot):
    os.environ["STREAM_PASSWORD"] = os.getenv("STREAM_PASSWORD", input('Enter stream password: '))
    live_robot.media.start_streams()



