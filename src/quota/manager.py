import asyncio
from datetime import datetime

from src.quota.profile import QuotaProfile
from src.quota.usage import DailyQuotaUsage


class QuotaManager:
    def __init__(self, profile: QuotaProfile | None = None):
        self._usages: dict[str, DailyQuotaUsage] = {}
        self._usage_mutex = asyncio.Lock()
        self._profile = profile or QuotaProfile()

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    async def get_usage(self, user_id: str) -> DailyQuotaUsage:
        async with self._usage_mutex:
            key = f"{user_id}:{self._today()}"
            if key not in self._usages:
                self._usages[key] = DailyQuotaUsage(user_id=user_id, date=self._today())
            return self._usages[key]

    def cleanup_old_usages(self) -> None:
        """Remove usage records from previous days."""
        today = self._today()
        keys_to_remove = [k for k in self._usages if not k.endswith(f":{today}")]
        for k in keys_to_remove:
            self._usages.pop(k, None)

    async def record_call_self(self, user_id: str) -> None:
        usage = await self.get_usage(user_id)
        usage.increment_call_self()

    async def record_chat(self, user_id: str) -> None:
        usage = await self.get_usage(user_id)
        usage.increment_chat()

    async def set_chat_replied(self, user_id: str) -> None:
        usage = await self.get_usage(user_id)
        usage.chat_user_replied = True

    async def check_call_allowed(self, user_id: str) -> tuple[bool, str]:
        usage = await self.get_usage(user_id)
        if not usage.can_call_self(self._profile):
            return False, "Daily call limit reached"
        if not usage.can_call_with_interval(self._profile.min_call_interval_seconds):
            return False, "Call interval too short"
        if not usage.can_call_in_hour(self._profile, self._profile.max_call_per_hour):
            return False, "Hourly call limit reached"
        return True, ""

    async def check_chat_allowed(self, user_id: str) -> tuple[bool, str]:
        usage = await self.get_usage(user_id)
        if not usage.can_chat(self._profile):
            return False, "Daily chat limit reached"
        return True, ""