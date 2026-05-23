import asyncio

from src.channels._escape import escape_output
from src.channels.base import BaseChannel
from src.core.constants import ChannelType, ChannelState


class VoiceChannel(BaseChannel):
    """Simulates phone calls."""

    def __init__(self):
        self._states: dict[str, ChannelState] = {}
        self._mutex = asyncio.Lock()

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.VOICE

    def _get_state(self, user_id: str) -> ChannelState:
        return self._states.get(user_id, ChannelState.IDLE)

    async def _set_state(self, user_id: str, state: ChannelState) -> None:
        async with self._mutex:
            self._states[user_id] = state

    async def send(self, user_id: str, content: str) -> dict:
        safe_content = escape_output(content)
        return {"status": "sent", "channel": "voice", "content": safe_content}

    async def call(self, user_id: str) -> dict:
        state = self._get_state(user_id)
        if state == ChannelState.IDLE:
            await self._set_state(user_id, ChannelState.OUTGOING)
        return {"status": "calling", "channel": "voice"}

    async def on_answered(self, user_id: str) -> dict:
        state = self._get_state(user_id)
        if state == ChannelState.OUTGOING:
            await self._set_state(user_id, ChannelState.INTERACTING)
        return {"status": "connected", "channel": "voice"}

    async def hangup(self, user_id: str) -> dict:
        await self._set_state(user_id, ChannelState.CLOSED)
        return {"status": "closed", "channel": "voice"}
