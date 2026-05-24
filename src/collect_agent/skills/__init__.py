"""Skills package for debt collection agent."""

from collect_agent.skills.base import (
    Skill,
    SkillContext,
    SkillResult,
    SkillResultStatus,
    ToolCallRecord,
)
from collect_agent.skills.complaint_skill import ComplaintSkill
from collect_agent.skills.crisis_skill import CrisisSkill
from collect_agent.skills.dispute_skill import DisputeSkill
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.followup_skill import FollowUpSkill
from collect_agent.skills.negotiation_skill import NegotiationSkill
from collect_agent.skills.onboard_skill import OnboardSkill
from collect_agent.skills.payment_guidance_skill import PaymentGuidanceSkill
from collect_agent.skills.reengage_skill import ReEngageSkill
from collect_agent.skills.registry import SkillRegistry
from collect_agent.skills.stop_skill import StopSkill
from collect_agent.skills.troubleshoot_skill import TroubleshootSkill

__all__ = [
    "Skill",
    "SkillContext",
    "SkillResult",
    "SkillResultStatus",
    "ToolCallRecord",
    "SkillExecutor",
    "SkillRegistry",
    "OnboardSkill",
    "PaymentGuidanceSkill",
    "NegotiationSkill",
    "ReEngageSkill",
    "DisputeSkill",
    "ComplaintSkill",
    "CrisisSkill",
    "StopSkill",
    "TroubleshootSkill",
    "FollowUpSkill",
]
