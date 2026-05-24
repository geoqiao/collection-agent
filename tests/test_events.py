import pytest
from collect_agent.events.router import EventRouter
from collect_agent.core.constants import EventType
from collect_agent.core.models import Event


class MockSessionManager:
    def __init__(self):
        self.events = []

    def get_or_create(self, user_id: str):
        return MockSession(self, user_id)


class MockSession:
    def __init__(self, manager, user_id: str):
        self.user_id = user_id
        self.manager = manager

    def handle_event(self, event: Event) -> None:
        self.manager.events.append((self.user_id, event))


@pytest.fixture
def router():
    return EventRouter(MockSessionManager())


def test_route_event_to_session(router):
    event = Event(user_id="u001", type=EventType.USER_LOGIN)
    router.route(event)
    assert len(router.session_manager.events) == 1
    assert router.session_manager.events[0][0] == "u001"
    assert router.session_manager.events[0][1].type == EventType.USER_LOGIN


def test_route_creates_session_for_new_user(router):
    event = Event(user_id="u_new", type=EventType.SCHEDULED_OUTREACH)
    router.route(event)
    assert len(router.session_manager.events) == 1
