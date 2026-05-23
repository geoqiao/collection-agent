import asyncio

from src.core.constants import ChannelType
from src.orchestrator.lock import InteractionLock
from src.quota.manager import QuotaManager
from src.compliance.checker import ComplianceChecker


class Orchestrator:
    PRIORITY = {
        ChannelType.VOICE: 3,
        ChannelType.CHATBOT: 2,
        ChannelType.PUSH: 1,
    }

    def __init__(self):
        self._locks: dict[str, InteractionLock] = {}
        self._lock_mutex = asyncio.Lock()
        self._quota = QuotaManager()
        self._compliance = ComplianceChecker()

    async def get_lock(self, user_id: str) -> InteractionLock:
        async with self._lock_mutex:
            if user_id not in self._locks:
                self._locks[user_id] = InteractionLock()
            return self._locks[user_id]

    def release_and_cleanup_lock(self, user_id: str) -> None:
        """Release lock and remove from dict to prevent memory leak."""
        if user_id in self._locks:
            self._locks[user_id].release()
            self._locks.pop(user_id, None)

    async def arbitrate(self, user_id: str, channel: ChannelType) -> str:
        lock = await self.get_lock(user_id)

        if not lock.is_locked:
            lock.acquire(channel)
            return "granted"

        if lock.holder == channel:
            return "granted"

        if self.PRIORITY[channel] > self.PRIORITY[lock.holder]:
            lock.acquire(channel)
            return "granted"

        return "deferred"

    async def select_channel(self, user) -> ChannelType | None:
        if not self._compliance.is_within_valid_hours():
            return None

        call_ok, _ = await self._quota.check_call_allowed(user.user_id)
        chat_ok, _ = await self._quota.check_chat_allowed(user.user_id)

        if call_ok:
            return ChannelType.VOICE
        if chat_ok:
            return ChannelType.CHATBOT
        return ChannelType.PUSH

    def can_contact_user(self, user) -> tuple[bool, str]:
        if not self._compliance.is_within_valid_hours():
            return False, "Outside valid hours"
        return True, ""
