import os
import logging
import sys

import pytest

os.environ['LOGLEVEL'] = 'debug'
loglevel = getattr(logging, os.getenv('LOGLEVEL', 'INFO').upper())

from mebo import Mebo


@pytest.mark.live_robot
def test_live_capture():
    os.environ['STREAM_PASSWORD'] = input('Enter stream password: ')
    m = Mebo(auto_connect=True)
    m.media.start_streams()
