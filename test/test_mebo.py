import pytest

from mebo.mebo import Component


@pytest.mark.parametrize(
    'component,actions,expected', [
        ('Foo', {'bar': list}, []),
    ]
)
def test_component_factory(component, actions, expected):
    c = Component.from_parent(component, **actions)
    assert c.__class__.__name__ == component
    assert c.actions == actions.keys()
    assert c.bar() == expected
