import pytest

from mebo.robot import ComponentFactory


@pytest.mark.parametrize(
    'component,actions,expected', [
        ('Foo', {'bar': list}, []),
    ]
)
def test_component_factory(component, actions, expected):
    c = ComponentFactory._from_parent(component, **actions)
    assert c.__class__.__name__ == component
    assert c.actions == actions.keys()
    assert c.bar() == expected
