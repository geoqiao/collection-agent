"""Tests for SkillRegistry."""

from src.skills.base import Skill, SkillContext, SkillResult
from src.skills.complaint_skill import ComplaintSkill
from src.skills.dispute_skill import DisputeSkill
from src.skills.negotiation_skill import NegotiationSkill
from src.skills.onboard_skill import OnboardSkill
from src.skills.registry import SkillRegistry
from src.skills.stop_skill import StopSkill


def test_register_and_get():
    registry = SkillRegistry()
    skill = DisputeSkill()
    registry.register(skill)
    assert registry.get("dispute_resolution") is skill


def test_select_skill_by_intent():
    registry = SkillRegistry()
    dispute = DisputeSkill()
    complaint = ComplaintSkill()
    registry.register(dispute)
    registry.register(complaint)

    selected = registry.select_skill(intent="D")
    assert selected is dispute

    selected = registry.select_skill(intent="E")
    assert selected is complaint


def test_select_skill_not_found():
    registry = SkillRegistry()
    assert registry.select_skill(intent="Z") is None


def test_list_skills():
    registry = SkillRegistry()
    registry.register(DisputeSkill())
    registry.register(ComplaintSkill())
    skills = registry.list_skills()
    assert len(skills) == 2


def test_register_requires_name():
    registry = SkillRegistry()

    class NoNameSkill(Skill):
        name = ""

        async def execute(self, ctx: SkillContext) -> SkillResult:
            return SkillResult()

    try:
        registry.register(NoNameSkill())
        assert False, "Expected ValueError"
    except ValueError:
        pass
