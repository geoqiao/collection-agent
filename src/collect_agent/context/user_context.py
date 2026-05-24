from collections import Counter
from datetime import datetime

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: str
    total_overdue_days: int = 0
    total_contacts: int = 0  # Total times contacted
    successful_contacts: int = 0  # Times user responded
    payment_promises: list[dict] = Field(
        default_factory=list
    )  # [{"date": "", "amount": 0, "status": "pending"}]
    preferred_channel: str | None = None  # User's most responsive channel
    intent_history: list[dict] = Field(
        default_factory=list
    )  # [{"intent": "", "timestamp": ""}]
    escalation_level: int = 0  # 0=normal, 1=supervisor, 2=legal
    notes: str = ""

    def record_contact(self, channel: str, user_responded: bool) -> None:
        self.total_contacts += 1
        if user_responded:
            self.successful_contacts += 1
        # Update preferred channel
        if user_responded:
            self.preferred_channel = channel

    def record_intent(self, intent: str) -> None:
        self.intent_history.append(
            {
                "intent": intent,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def record_payment_promise(self, date: str, amount: float) -> None:
        self.payment_promises.append(
            {
                "date": date,
                "amount": amount,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
        )

    def mark_promise_kept(self, promise_index: int) -> None:
        if 0 <= promise_index < len(self.payment_promises):
            self.payment_promises[promise_index]["status"] = "kept"

    def escalate(self) -> None:
        self.escalation_level = min(self.escalation_level + 1, 2)

    def get_response_rate(self) -> float:
        if self.total_contacts == 0:
            return 0.0
        return self.successful_contacts / self.total_contacts

    def get_dominant_intent(self, last_n: int = 5) -> str | None:
        if not self.intent_history:
            return None
        recent = self.intent_history[-last_n:]
        intents = [h["intent"] for h in recent]
        return Counter(intents).most_common(1)[0][0]
