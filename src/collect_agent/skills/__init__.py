"""Skills package for debt collection agent."""

from collect_agent.skills.base import Skill, SkillResult
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.loader import SkillLoader
from collect_agent.skills.registry import SkillRegistry

__all__ = [
    "Skill",
    "SkillResult",
    "SkillExecutor",
    "SkillLoader",
    "SkillRegistry",
]
