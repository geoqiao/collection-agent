import asyncio

from src.channels.base import BaseChannel
from src.core.constants import ChannelType, ChannelState


class ChatbotChannel(BaseChannel):
    """Simulates WhatsApp/SMS messaging."""

    def __init__(self):
        self._states: dict[str, ChannelState] = {}
        self._mutex = asyncio.Lock()

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.CHATBOT

    def _get_state(self, user_id: str) -> ChannelState:
        return self._states.get(user_id, ChannelState.IDLE)

    async def _set_state(self, user_id: str, state: ChannelState) -> None:
        async with self._mutex:
            self._states[user_id] = state

    async def send(self, user_id: str, content: str) -> dict:
        state = self._get_state(user_id)
        if state == ChannelState.IDLE:
            await self._set_state(user_id, ChannelState.OUTGOING)
        elif state == ChannelState.OUTGOING:
            await self._set_state(user_id, ChannelState.WAITING_REPLY)
        return {"status": "sent", "channel": "chatbot"}

    async def receive(self, user_id: str, content: str) -> None:
        state = self._get_state(user_id)
        if state == ChannelState.WAITING_REPLY:
            await self._set_state(user_id, ChannelState.INTERACTING)

    async def close(self, user_id: str) -> dict:
        await self._set_state(user_id, ChannelState.CLOSED)
        return {"status": "closed", "channel": "chatbot"}
