import pytest

from collect_agent.channels.base import BaseChannel
from collect_agent.channels.chatbot import ChatbotChannel
from collect_agent.channels.push import PushChannel
from collect_agent.channels.registry import ChannelRegistry, create_default_registry
from collect_agent.channels.voice import VoiceChannel
from collect_agent.core.constants import ChannelState, ChannelType


class MockChannel(BaseChannel):
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.CHATBOT

    async def send(self, user_id: str, content: str) -> dict:
        return {"status": "sent", "channel": "chatbot"}


@pytest.fixture
def registry():
    return ChannelRegistry()


def test_register_channel(registry):
    ch = MockChannel()
    registry.register(ch)
    assert registry.get(ChannelType.CHATBOT) is ch


def test_get_state(registry):
    ch = MockChannel()
    registry.register(ch)
    assert registry.get_state(ChannelType.CHATBOT) == ChannelState.IDLE


def test_set_state(registry):
    ch = MockChannel()
    registry.register(ch)
    registry.set_state(ChannelType.CHATBOT, ChannelState.OUTGOING)
    assert registry.get_state(ChannelType.CHATBOT) == ChannelState.OUTGOING


def test_get_all_states(registry):
    ch = MockChannel()
    registry.register(ch)
    states = registry.get_all_states()
    assert "chatbot" in states


# ChatbotChannel tests


@pytest.mark.asyncio
async def test_chatbot_send_returns_dict():
    ch = ChatbotChannel()
    result = await ch.send("user1", "Hello")
    assert result["status"] == "sent"
    assert result["channel"] == "chatbot"
    assert result["content"] == "Hello"


@pytest.mark.asyncio
async def test_chatbot_state_transitions():
    ch = ChatbotChannel()
    user_id = "user1"

    assert ch._get_state(user_id) == ChannelState.IDLE

    await ch.send(user_id, "Hello")
    assert ch._get_state(user_id) == ChannelState.OUTGOING

    await ch.send(user_id, "Follow up")
    assert ch._get_state(user_id) == ChannelState.WAITING_REPLY

    await ch.receive(user_id, "Hi there")
    assert ch._get_state(user_id) == ChannelState.INTERACTING

    await ch.close(user_id)
    assert ch._get_state(user_id) == ChannelState.CLOSED


@pytest.mark.asyncio
async def test_chatbot_channel_type():
    ch = ChatbotChannel()
    assert ch.channel_type == ChannelType.CHATBOT


# VoiceChannel tests


@pytest.mark.asyncio
async def test_voice_call_returns_dict():
    ch = VoiceChannel()
    result = await ch.call("user1")
    assert result == {"status": "calling", "channel": "voice"}


@pytest.mark.asyncio
async def test_voice_state_transitions():
    ch = VoiceChannel()
    user_id = "user1"

    assert ch._get_state(user_id) == ChannelState.IDLE

    await ch.call(user_id)
    assert ch._get_state(user_id) == ChannelState.OUTGOING

    await ch.on_answered(user_id)
    assert ch._get_state(user_id) == ChannelState.INTERACTING

    await ch.hangup(user_id)
    assert ch._get_state(user_id) == ChannelState.CLOSED


@pytest.mark.asyncio
async def test_voice_channel_type():
    ch = VoiceChannel()
    assert ch.channel_type == ChannelType.VOICE


# PushChannel tests


@pytest.mark.asyncio
async def test_push_send_returns_dict():
    ch = PushChannel()
    result = await ch.send("user1", "Notification")
    assert result["status"] == "sent"
    assert result["channel"] == "push"
    assert result["content"] == "Notification"


@pytest.mark.asyncio
async def test_push_state_transitions():
    ch = PushChannel()
    user_id = "user1"

    assert ch._get_state(user_id) == ChannelState.IDLE

    await ch.send(user_id, "Notification")
    assert ch._get_state(user_id) == ChannelState.OUTGOING

    await ch.send(user_id, "Another notification")
    assert ch._get_state(user_id) == ChannelState.CLOSED


@pytest.mark.asyncio
async def test_push_channel_type():
    ch = PushChannel()
    assert ch.channel_type == ChannelType.PUSH


# XSS escape tests


@pytest.mark.asyncio
async def test_chatbot_escapes_xss():
    ch = ChatbotChannel()
    malicious = '<script>alert("xss")</script>'
    result = await ch.send("user1", malicious)
    escaped = "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"
    assert result["content"] == escaped


@pytest.mark.asyncio
async def test_push_escapes_xss():
    ch = PushChannel()
    malicious = "<img src=x onerror=alert(1)>"
    result = await ch.send("user1", malicious)
    assert result["content"].startswith("&lt;")
    assert result["content"].endswith("&gt;")
    # Angle brackets are escaped, so the tag cannot execute
    assert "<img" not in result["content"]


@pytest.mark.asyncio
async def test_voice_escapes_xss():
    ch = VoiceChannel()
    malicious = "<body onload=alert(1)>"
    result = await ch.send("user1", malicious)
    assert result["content"].startswith("&lt;")
    assert result["content"].endswith("&gt;")
    assert "<body" not in result["content"]


@pytest.mark.asyncio
async def test_empty_content_not_modified():
    ch = ChatbotChannel()
    result = await ch.send("user1", "")
    assert result["content"] == ""


# Factory test


def test_create_default_registry():
    registry = create_default_registry()
    assert registry.get(ChannelType.CHATBOT) is not None
    assert registry.get(ChannelType.VOICE) is not None
    assert registry.get(ChannelType.PUSH) is not None

    assert isinstance(registry.get(ChannelType.CHATBOT), ChatbotChannel)
    assert isinstance(registry.get(ChannelType.VOICE), VoiceChannel)
    assert isinstance(registry.get(ChannelType.PUSH), PushChannel)

    states = registry.get_all_states()
    assert "chatbot" in states
    assert "voice" in states
    assert "push" in states
