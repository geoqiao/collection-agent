import asyncio

from collect_agent.channels._escape import escape_output
from collect_agent.channels.base import BaseChannel
from collect_agent.core.constants import ChannelState, ChannelType


class PushChannel(BaseChannel):
    """Simulates App Push notifications."""

    def __init__(self):
        self._states: dict[str, ChannelState] = {}
        self._mutex = asyncio.Lock()

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.PUSH

    def _get_state(self, user_id: str) -> ChannelState:
        return self._states.get(user_id, ChannelState.IDLE)

    async def _set_state(self, user_id: str, state: ChannelState) -> None:
        async with self._mutex:
            self._states[user_id] = state

    async def send(self, user_id: str, content: str) -> dict:
        safe_content = escape_output(content)
        state = self._get_state(user_id)
        if state == ChannelState.IDLE:
            await self._set_state(user_id, ChannelState.OUTGOING)
        elif state == ChannelState.OUTGOING:
            await self._set_state(user_id, ChannelState.CLOSED)
        return {"status": "sent", "channel": "push", "content": safe_content}
