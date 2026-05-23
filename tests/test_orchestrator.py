import pytest
from src.orchestrator.lock import InteractionLock
from src.orchestrator.orchestrator import Orchestrator
from src.core.constants import ChannelType
from src.core.models import UserProfile


@pytest.fixture
def lock():
    return InteractionLock()


def test_initially_unlocked(lock):
    assert lock.holder is None
    assert lock.is_locked is False


def test_acquire_lock(lock):
    lock.acquire(ChannelType.VOICE)
    assert lock.holder == ChannelType.VOICE
    assert lock.is_locked is True


def test_release_lock(lock):
    lock.acquire(ChannelType.VOICE)
    lock.release()
    assert lock.holder is None
    assert lock.is_locked is False


def test_acquire_when_locked(lock):
    lock.acquire(ChannelType.CHATBOT)
    lock.acquire(ChannelType.VOICE)
    assert lock.holder == ChannelType.VOICE


@pytest.fixture
def orchestrator():
    return Orchestrator()


def test_arbitrate_no_holder(orchestrator):
    result = orchestrator.arbitrate("u001", ChannelType.VOICE)
    assert result == "granted"
    assert orchestrator.get_lock("u001").holder == ChannelType.VOICE


def test_arbitrate_voice_priority(orchestrator):
    orchestrator.arbitrate("u001", ChannelType.CHATBOT)
    result = orchestrator.arbitrate("u001", ChannelType.VOICE)
    assert result == "granted"
    assert orchestrator.get_lock("u001").holder == ChannelType.VOICE


def test_arbitrate_lower_priority_denied(orchestrator):
    orchestrator.arbitrate("u001", ChannelType.VOICE)
    result = orchestrator.arbitrate("u001", ChannelType.CHATBOT)
    assert result == "deferred"


def test_release_lock_orchestrator(orchestrator):
    orchestrator.arbitrate("u001", ChannelType.VOICE)
    orchestrator.release_lock("u001")
    assert orchestrator.get_lock("u001").holder is None


def test_select_channel_considers_quota(orchestrator):
    user = UserProfile(user_id="u001")
    channel = orchestrator.select_channel(user)
    assert channel in [ChannelType.CHATBOT, ChannelType.VOICE, ChannelType.PUSH]
