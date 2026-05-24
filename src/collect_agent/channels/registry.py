from collect_agent.channels.base import BaseChannel
from collect_agent.core.constants import ChannelState, ChannelType


def create_default_registry() -> "ChannelRegistry":
    registry = ChannelRegistry()
    from collect_agent.channels.chatbot import ChatbotChannel
    from collect_agent.channels.push import PushChannel
    from collect_agent.channels.voice import VoiceChannel

    registry.register(ChatbotChannel())
    registry.register(VoiceChannel())
    registry.register(PushChannel())
    return registry


class ChannelRegistry:
    def __init__(self):
        self._channels: dict[ChannelType, BaseChannel] = {}
        self._states: dict[ChannelType, ChannelState] = {}

    def register(self, channel: BaseChannel) -> None:
        self._channels[channel.channel_type] = channel
        self._states[channel.channel_type] = ChannelState.IDLE

    def get(self, channel_type: ChannelType) -> BaseChannel | None:
        return self._channels.get(channel_type)

    def get_state(self, channel_type: ChannelType) -> ChannelState:
        return self._states.get(channel_type, ChannelState.IDLE)

    def set_state(self, channel_type: ChannelType, state: ChannelState) -> None:
        self._states[channel_type] = state

    def get_all_states(self) -> dict[str, str]:
        return {ct.value: cs.value for ct, cs in self._states.items()}

    def pause(self, channel_type: ChannelType) -> None:
        if self._states.get(channel_type) == ChannelState.INTERACTING:
            self._states[channel_type] = ChannelState.PAUSED

    def resume(self, channel_type: ChannelType) -> None:
        if self._states.get(channel_type) == ChannelState.PAUSED:
            self._states[channel_type] = ChannelState.WAITING_REPLY
