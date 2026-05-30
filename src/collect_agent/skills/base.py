"""Skill framework base classes — simplified for MVP.

Skills are declarative configuration, not Python classes with inheritance.
Execution logic is fully delegated to SkillExecutor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    """Result of skill execution."""

    status: str = "success"
    response_text: str | None = None
    new_session_state: str | None = None
    escalation: bool = False
    requires_follow_up: bool = False
    thinking: str = ""
    actions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Skill:
    """A skill defines configuration for the ReAct executor.

    Skills do NOT contain hard-coded execution logic.
    Loaded from Markdown files with YAML frontmatter.
    """

    name: str = ""
    description: str = ""
    tools: list[str] = field(default_factory=list)
    max_steps: int = 1000
    content: str = ""  # Markdown body used as system prompt supplement

    def get_system_prompt(self) -> str:
        """Build the system prompt for this skill."""
        lines = [
            f"# Skill: {self.name}",
            f"## 描述\n{self.description}",
        ]

        if self.tools:
            lines.append("## 可用工具")
            for t in self.tools:
                lines.append(f"- {t}")

        if self.content:
            lines.append(f"\n## 详细指令\n{self.content}")

        return "\n\n".join(lines)
