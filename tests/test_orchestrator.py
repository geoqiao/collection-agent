import pytest
from unittest.mock import patch

from collect_agent.orchestrator.lock import InteractionLock
from collect_agent.orchestrator.orchestrator import Orchestrator
from collect_agent.core.constants import ChannelType
from collect_agent.core.models import UserProfile


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


@pytest.mark.asyncio
async def test_arbitrate_no_holder(orchestrator):
    result = await orchestrator.arbitrate("u001", ChannelType.VOICE)
    assert result == "granted"
    lock = await orchestrator.get_lock("u001")
    assert lock.holder == ChannelType.VOICE


@pytest.mark.asyncio
async def test_arbitrate_voice_priority(orchestrator):
    await orchestrator.arbitrate("u001", ChannelType.CHATBOT)
    result = await orchestrator.arbitrate("u001", ChannelType.VOICE)
    assert result == "granted"
    lock = await orchestrator.get_lock("u001")
    assert lock.holder == ChannelType.VOICE


@pytest.mark.asyncio
async def test_arbitrate_lower_priority_denied(orchestrator):
    await orchestrator.arbitrate("u001", ChannelType.VOICE)
    result = await orchestrator.arbitrate("u001", ChannelType.CHATBOT)
    assert result == "deferred"


@pytest.mark.asyncio
async def test_release_lock_orchestrator(orchestrator):
    await orchestrator.arbitrate("u001", ChannelType.VOICE)
    orchestrator.release_and_cleanup_lock("u001")
    lock = await orchestrator.get_lock("u001")
    assert lock.holder is None


@pytest.mark.asyncio
async def test_select_channel_considers_quota(orchestrator):
    with patch.object(
        orchestrator._compliance, "is_within_valid_hours", return_value=True
    ):
        user = UserProfile(user_id="u001")
        channel = await orchestrator.select_channel(user)
        assert channel in [ChannelType.CHATBOT, ChannelType.VOICE, ChannelType.PUSH]


@pytest.mark.asyncio
async def test_lock_cleanup_removes_from_dict(orchestrator):
    await orchestrator.arbitrate("u001", ChannelType.VOICE)
    assert "u001" in orchestrator._locks
    orchestrator.release_and_cleanup_lock("u001")
    assert "u001" not in orchestrator._locks
