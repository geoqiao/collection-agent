from pydantic import BaseModel


class QuotaProfile(BaseModel):
    call_self_daily_max: int = 10
    call_contact_daily_max: int = 10
    call_answer_daily_max: int = 3
    chat_unanswered_daily_max: int = 5
    chat_answered_daily_max: int = 100
    push_daily_max: int = 1
    valid_hours: tuple[int, int] = (8, 20)
    max_call_per_hour: int = 3
    min_call_interval_seconds: int = 600
    min_chat_interval_unanswered: int = 1800
    min_chat_interval_answered: int = 120