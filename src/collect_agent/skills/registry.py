"""Skill registry for managing and discovering skills."""

from __future__ import annotations

from collect_agent.core.models import UserProfile
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

    def select_skill(
        self,
        intent: str,
        event_type: str | None = None,
        user_profile: UserProfile | None = None,
    ) -> Skill | None:
        """Select a skill based on intent and optional context.

        Matches the intent against each skill's triggers.
        Returns the first matching skill or None if no match.
        """
        for skill in self._skills.values():
            if intent in skill.triggers:
                return skill
        return None

    def get(self, name: str) -> Skill | None:
        """Retrieve a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[Skill]:
        """Return all registered skills."""
        return list(self._skills.values())
