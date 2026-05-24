"""Pydantic models for prompt components."""

from pydantic import BaseModel, Field
from typing import Any


class PromptFragment(BaseModel):
    name: str
    content: str
    priority: int = 0


class SkillPromptConfig(BaseModel):
    skill_name: str
    constitutional_rules: str = ""
    cot_sop: str = ""
    xml_schema: str = ""
    few_shots: str = ""
    dynamic_context: str = ""


class ToolDescription(BaseModel):
    name: str
    description: str
    parameters: list[dict[str, Any]] = Field(default_factory=list)


class ParsedAction(BaseModel):
    action_type: str = ""  # "reply", "tool_call", "escalate", "end"
    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    follow_up: bool = False


class ParsedIntent(BaseModel):
    category: str = ""
    confidence: str = ""
    escalation: bool = False
    emotion: str = ""


class ParsedXMLResponse(BaseModel):
    thinking: str = ""
    intent: ParsedIntent = Field(default_factory=ParsedIntent)
    action: ParsedAction = Field(default_factory=ParsedAction)
    final_message: str = ""
