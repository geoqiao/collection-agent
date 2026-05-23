from src.channels.base import BaseChannel
from src.core.constants import ChannelType, ChannelState


class PushChannel(BaseChannel):
    """Simulates App Push notifications."""

    def __init__(self):
        self._states: dict[str, ChannelState] = {}

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.PUSH

    def _get_state(self, user_id: str) -> ChannelState:
        return self._states.get(user_id, ChannelState.IDLE)

    def _set_state(self, user_id: str, state: ChannelState) -> None:
        self._states[user_id] = state

    async def send(self, user_id: str, content: str) -> dict:
        state = self._get_state(user_id)
        if state == ChannelState.IDLE:
            self._set_state(user_id, ChannelState.OUTGOING)
        elif state == ChannelState.OUTGOING:
            self._set_state(user_id, ChannelState.CLOSED)
        return {"status": "sent", "channel": "push"}
