import pytest
from src.session.state_machine import SessionStateMachine
from src.core.constants import SessionState


@pytest.fixture
def sm():
    return SessionStateMachine()


def test_initial_state(sm):
    assert sm.current == SessionState.IDLE


def test_transition_idle_to_outreach(sm):
    assert sm.can_transition(SessionState.OUTREACH_START) is True
    sm.transition(SessionState.OUTREACH_START)
    assert sm.current == SessionState.OUTREACH_START


def test_invalid_transition(sm):
    sm.transition(SessionState.OUTREACH_START)
    assert sm.can_transition(SessionState.RESOLVED) is False


def test_transition_to_intent_detected(sm):
    sm.transition(SessionState.OUTREACH_START)
    sm.transition(SessionState.INTENT_DETECTED)
    assert sm.current == SessionState.INTENT_DETECTED


def test_transition_to_resolved(sm):
    sm.transition(SessionState.OUTREACH_START)
    sm.transition(SessionState.INTENT_DETECTED)
    sm.transition(SessionState.FOLLOW_UP)
    sm.transition(SessionState.RESOLVED)
    assert sm.current == SessionState.RESOLVED
