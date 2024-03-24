"""To run these tests: `py.test -m 'live_robot'`"""

import os
import time

import pytest

from mebo import Mebo
from mebo.robot import DIRECTIONS

os.environ["LOGLEVEL"] = "debug"


@pytest.fixture(scope="session")
def live_robot():
    return Mebo()


@pytest.mark.live_robot
@pytest.mark.parametrize("direction", DIRECTIONS)
def test_live_robot_movement(live_robot, direction):
    live_robot.move(direction)
    time.sleep(1.0)
    assert True


@pytest.mark.media
@pytest.mark.live_robot
def test_live_stream_capture(live_robot):
    os.environ["STREAM_PASSWORD"] = os.getenv(
        "STREAM_PASSWORD", input("Enter stream password: ")
    )
    live_robot.media.start_streams()
