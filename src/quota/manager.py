from datetime import datetime
from src.quota.profile import QuotaProfile
from src.quota.usage import DailyQuotaUsage


class QuotaManager:
    def __init__(self):
        self._usages: dict[str, DailyQuotaUsage] = {}
        self._profile = QuotaProfile()

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def get_usage(self, user_id: str) -> DailyQuotaUsage:
        key = f"{user_id}:{self._today()}"
        if key not in self._usages:
            self._usages[key] = DailyQuotaUsage(user_id=user_id, date=self._today())
        return self._usages[key]

    def record_call_self(self, user_id: str) -> None:
        usage = self.get_usage(user_id)
        usage.increment_call_self()

    def record_chat(self, user_id: str) -> None:
        usage = self.get_usage(user_id)
        usage.increment_chat()

    def set_chat_replied(self, user_id: str) -> None:
        usage = self.get_usage(user_id)
        usage.chat_user_replied = True

    def check_call_allowed(self, user_id: str) -> tuple[bool, str]:
        usage = self.get_usage(user_id)
        if not usage.can_call_self(self._profile):
            return False, "Daily call limit reached"
        if not usage.can_call_with_interval(self._profile.min_call_interval_seconds):
            return False, "Call interval too short"
        if not usage.can_call_in_hour(self._profile, self._profile.max_call_per_hour):
            return False, "Hourly call limit reached"
        return True, ""

    def check_chat_allowed(self, user_id: str) -> tuple[bool, str]:
        usage = self.get_usage(user_id)
        if not usage.can_chat(self._profile):
            return False, "Daily chat limit reached"
        return True, ""