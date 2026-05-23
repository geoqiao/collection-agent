import pytest
from src.channels.base import BaseChannel
from src.channels.registry import ChannelRegistry, create_default_registry
from src.channels.chatbot import ChatbotChannel
from src.channels.voice import VoiceChannel
from src.channels.push import PushChannel
from src.core.constants import ChannelType, ChannelState


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
    assert result == {"status": "sent", "channel": "chatbot"}


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
    assert result == {"status": "sent", "channel": "push"}


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
