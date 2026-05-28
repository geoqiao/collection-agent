"""Skill registry — simplified, no triggers, no hard-coded selection.

Skill selection is delegated to the LLM via Decider.
Registry only stores and retrieves by name.
"""

from __future__ import annotations

from collect_agent.skills.base import Skill


class SkillRegistry:
    """Registry for collecting and retrieving skills."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill instance."""
        if not skill.name:
            raise ValueError("Skill must have a name")
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """Retrieve a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[Skill]:
        """Return all registered skills."""
        return list(self._skills.values())
