"""Skill framework base classes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from collect_agent.core.models import Message, UserProfile
from collect_agent.tools.base import Tool


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


@dataclass
class Skill:
    """A skill defines configuration for the ReAct executor.

    Skills do NOT contain hard-coded execution logic.
    Execution is fully delegated to SkillExecutor, which drives an LLM
    through a ReAct loop using the skill's system prompt and available tools.
    """

    name: str = ""
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    is_one_way_door: bool = False
    max_react_steps: int = 5
    prompt_template: str = ""  # Filename under prompts/templates/skills/
    tools: list[Tool] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Read class-level overrides from subclasses."""
        cls = self.__class__
        defaults = {
            "name": "",
            "description": "",
            "triggers": [],
            "is_one_way_door": False,
            "max_react_steps": 5,
            "prompt_template": "",
        }
        for attr, default in defaults.items():
            if attr in cls.__dict__ and getattr(self, attr) == default:
                object.__setattr__(self, attr, cls.__dict__[attr])

    def get_available_tools(self) -> list[Tool]:
        return self.tools
