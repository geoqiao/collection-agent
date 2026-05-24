from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field

from collect_agent.core.constants import EventType


class UserProfile(BaseModel):
    user_id: str
    name: str = ""
    phone: str = ""
    occupation: str | None = None
    overdue_days: int = 0
    amount_due: float = 0.0

    @computed_field
    @property
    def is_sensitive(self) -> bool:
        if not self.occupation:
            return False
        sensitive = {
            "律师",
            "法官",
            "检察官",
            "警察",
            "政府官员",
            "公务员",
            "军人",
            "军人配偶",
            "记者",
            "媒体从业者",
        }
        return self.occupation in sensitive


class Event(BaseModel):
    user_id: str
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class Message(BaseModel):
    channel: str
    direction: str  # "inbound" | "outbound"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationContext(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    current_intent: str | None = None
    negotiation_round: int = 0

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]


class UserState(BaseModel):
    user_id: str
    profile: UserProfile
    session_state: str = "idle"
    channel_states: dict[str, str] = Field(default_factory=dict)
    conversation: ConversationContext = Field(default_factory=ConversationContext)
    quota_usage: dict[str, Any] = Field(default_factory=dict)
    paused_until: datetime | None = None
