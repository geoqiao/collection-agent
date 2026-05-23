import pytest
from src.orchestrator.lock import InteractionLock
from src.core.constants import ChannelType


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
