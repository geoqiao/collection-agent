import pytest
from src.channels.base import BaseChannel
from src.channels.registry import ChannelRegistry
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
