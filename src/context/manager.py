from src.context.window import ContextWindow
from src.context.user_context import UserContext


class ContextManager:
    def __init__(self, user_id: str, strategy: str = "sliding_window"):
        self.user_id = user_id
        self.window = ContextWindow(strategy=strategy)
        self.user_context = UserContext(user_id=user_id)

    def add_message(self, message) -> None:
        self.window.add_message(message)

    def get_llm_context(self) -> list[dict[str, str]]:
        return self.window.get_messages_for_llm()

    def get_user_context_summary(self) -> str:
        """Generate a summary of user context for prompt injection."""
        lines = [
            f"User ID: {self.user_id}",
            f"Total contacts: {self.user_context.total_contacts}",
            f"Response rate: {self.user_context.get_response_rate():.0%}",
            f"Escalation level: {self.user_context.escalation_level}",
        ]
        if self.user_context.preferred_channel:
            lines.append(f"Preferred channel: {self.user_context.preferred_channel}")
        dominant = self.user_context.get_dominant_intent()
        if dominant:
            lines.append(f"Recent dominant intent: {dominant}")
        if self.user_context.payment_promises:
            pending = [p for p in self.user_context.payment_promises if p["status"] == "pending"]
            if pending:
                lines.append(f"Pending promises: {len(pending)}")
        return "\n".join(lines)

    def record_contact(self, channel: str, user_responded: bool) -> None:
        self.user_context.record_contact(channel, user_responded)

    def record_intent(self, intent: str) -> None:
        self.user_context.record_intent(intent)

    def record_payment_promise(self, date: str, amount: float) -> None:
        self.user_context.record_payment_promise(date, amount)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "window": {
                "messages": [m.model_dump() for m in self.window.get_messages()],
                "summary": self.window._summary,
            },
            "user_context": self.user_context.model_dump(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextManager":
        cm = cls(data["user_id"])
        # Restore messages
        from src.core.models import Message
        for m_data in data.get("window", {}).get("messages", []):
            cm.window.add_message(Message(**m_data))
        cm.window._summary = data.get("window", {}).get("summary", "")
        cm.user_context = UserContext(**data.get("user_context", {}))
        return cm
