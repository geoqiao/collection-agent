import asyncio

from collect_agent.compliance.checker import ComplianceChecker
from collect_agent.core.constants import ChannelType
from collect_agent.orchestrator.lock import InteractionLock
from collect_agent.quota.manager import QuotaManager


class Orchestrator:
    PRIORITY = {
        ChannelType.VOICE: 3,
        ChannelType.CHATBOT: 2,
        ChannelType.PUSH: 1,
    }

    def __init__(
        self,
        quota_manager: QuotaManager | None = None,
        compliance_checker: ComplianceChecker | None = None,
    ):
        self._locks: dict[str, InteractionLock] = {}
        self._lock_mutex = asyncio.Lock()
        self._quota = quota_manager or QuotaManager()
        self._compliance = compliance_checker or ComplianceChecker()

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

    def is_within_compliance_hours(self) -> tuple[bool, str]:
        if not self._compliance.is_within_valid_hours():
            return False, "Outside valid hours"
        return True, ""
