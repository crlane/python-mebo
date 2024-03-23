import pytest

from mebo.robot import ComponentFactory, Mebo
from mebo.exceptions import (
    MeboConfigurationError,
    MeboCommandError,
)

@pytest.fixture
def loopback_mebo():
    return Mebo(ip='127.0.0.1', autoconnect=False)


@pytest.mark.parametrize(
    'component,actions,expected', [
        ('SomeComponent', {'get_list': list}, []),
    ]
)
def test_component_factory(component, actions, expected):
    c = ComponentFactory.build(component, **actions)
    assert c.__class__.__name__ == component
    assert c.actions == actions.keys()
    assert c.get_list() == expected


@pytest.mark.parametrize(
    'ip', [
        None,
        "192.168.1.1/24",
        "foobarbaz",
        "256.100.100.100",
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        192_168_001_001,
    ],
    ids = [None, "cidr", "string", "bad IP", "IPv6", "number"]
)
def test_construction_without_valid_ip(ip):
    with pytest.raises(MeboConfigurationError):
        _ = Mebo(ip=ip, autoconnect=False), 


def test_bad_move_direction(loopback_mebo):
    with pytest.raises(MeboCommandError):
        loopback_mebo.move('SSW')


def test_move_directions(loopback_mebo):
    assert len(loopback_mebo.move_directions) == 8
    assert loopback_mebo.move_directions['n'] == 'move_forward'
    assert loopback_mebo.move_directions['nw'] == 'move_forward_left'


def test_claw(loopback_mebo):
    assert list(loopback_mebo.claw.actions) == ['open', 'close', 'stop']


def test_wrist(loopback_mebo):
    assert list(loopback_mebo.wrist.actions) == [
        'rotate_right',
        'inch_right',
        'rotate_left',
        'inch_left',
        'rotate_stop',
        'up',
        'down',
        'lift_stop',
    ]


def test_arm(loopback_mebo):
    assert list(loopback_mebo.arm.actions) == [
        'up',
        'down',
        'stop',
    ]


def test_speaker(loopback_mebo):
    assert list(loopback_mebo.speaker.actions) == [
        'set_volume',
        'play_sound'
    ]
