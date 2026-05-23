"""Skill framework base classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.models import UserProfile, Message
from src.tools.base import Tool


class SkillResultStatus:
    SUCCESS = "success"
    NEEDS_ESCALATION = "needs_escalation"
    STOPPED = "stopped"
    CRISIS = "crisis"
    ERROR = "error"


@dataclass
class ToolCallRecord:
    tool_name: str
    parameters: dict[str, Any]
    result: dict[str, Any]


@dataclass
class SkillContext:
    user_id: str
    user_profile: UserProfile
    conversation_history: list[Message] = field(default_factory=list)
    current_intent: str = ""
    user_message: str | None = None
    session_state: str = "normal"
    available_tools: list[Tool] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    bill_facts: dict[str, Any] = field(default_factory=dict)
    negotiation_round: int = 0


@dataclass
class SkillResult:
    status: str = SkillResultStatus.SUCCESS
    response_text: str | None = None
    actions: list[ToolCallRecord] = field(default_factory=list)
    new_session_state: str | None = None
    escalation: bool = False
    requires_follow_up: bool = False
    follow_up_date: datetime | None = None
    thinking: str = ""


class Skill(ABC):
    name: str = ""
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    is_one_way_door: bool = False
    max_react_steps: int = 5

    def __init__(self, tools: list[Tool] | None = None):
        self.tools = tools or []

    @abstractmethod
    async def execute(self, ctx: SkillContext) -> SkillResult:
        pass

    def get_available_tools(self) -> list[Tool]:
        return self.tools
