import pytest
from src.main import CollectAgentSystem
from src.core.constants import EventType
from src.core.models import Event


@pytest.fixture
def system():
    return CollectAgentSystem()


def test_system_initialization(system):
    assert system.router is not None
    assert system.session_manager is not None


def test_handle_user_login_event(system):
    event = Event(user_id="u001", type=EventType.USER_LOGIN)
    system.handle_event(event)
    session = system.session_manager.get("u001")
    assert session is not None
    assert session.user_id == "u001"
