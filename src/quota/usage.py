from datetime import datetime, timedelta
from pydantic import BaseModel, Field


class DailyQuotaUsage(BaseModel):
    user_id: str
    date: str
    call_self_count: int = 0
    call_contact_count: int = 0
    call_answered_count: int = 0
    call_last_timestamp: datetime | None = None
    call_timestamps: list[datetime] = Field(default_factory=list)
    chat_sent_count: int = 0
    chat_user_replied: bool = False
    chat_last_timestamp: datetime | None = None
    push_sent_count: int = 0

    def increment_call_self(self) -> None:
        self.call_self_count += 1
        self.call_last_timestamp = datetime.now()
        self.call_timestamps.append(datetime.now())

    def can_call_self(self, profile) -> bool:
        return self.call_self_count < profile.call_self_daily_max

    def can_call_with_interval(self, min_seconds: int) -> bool:
        if self.call_last_timestamp is None:
            return True
        elapsed = (datetime.now() - self.call_last_timestamp).total_seconds()
        return elapsed >= min_seconds

    def can_call_in_hour(self, profile, max_per_hour: int) -> bool:
        hour_ago = datetime.now() - timedelta(hours=1)
        recent = [t for t in self.call_timestamps if t > hour_ago]
        return len(recent) < max_per_hour

    def increment_chat(self) -> None:
        self.chat_sent_count += 1
        self.chat_last_timestamp = datetime.now()

    def can_chat(self, profile) -> bool:
        if self.chat_user_replied:
            return self.chat_sent_count < profile.chat_answered_daily_max
        return self.chat_sent_count < profile.chat_unanswered_daily_max