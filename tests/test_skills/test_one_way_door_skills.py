"""Tests for one-way door skills."""

from __future__ import annotations

import pytest

from src.core.models import UserProfile
from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus
from src.skills.complaint_skill import ComplaintSkill
from src.skills.crisis_skill import CrisisSkill
from src.skills.dispute_skill import DisputeSkill
from src.skills.stop_skill import StopSkill
from src.tools.compliance import EscalateToHumanTool, PauseCollectionTool, WelfareAlertTool
from src.tools.user import AddToDncListTool


@pytest.mark.asyncio
async def test_dispute_skill_is_one_way_door():
    skill = DisputeSkill()
    assert skill.is_one_way_door is True
    assert "D" in skill.triggers
    assert skill.name == "dispute_resolution"


@pytest.mark.asyncio
async def test_dispute_skill_executes_tools():
    skill = DisputeSkill(tools=[PauseCollectionTool(), EscalateToHumanTool()])
    ctx = SkillContext(
        user_id="u1",
        user_profile=UserProfile(user_id="u1", name="Test"),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.new_session_state == "disputed"
    assert len(result.actions) == 2
    assert result.actions[0].tool_name == "pause_collection"
    assert result.actions[1].tool_name == "escalate_to_human"
    assert "争议" in result.response_text


@pytest.mark.asyncio
async def test_complaint_skill_is_one_way_door():
    skill = ComplaintSkill()
    assert skill.is_one_way_door is True
    assert "E" in skill.triggers
    assert skill.name == "complaint_handling"


@pytest.mark.asyncio
async def test_complaint_skill_executes_tools():
    skill = ComplaintSkill(tools=[PauseCollectionTool(), EscalateToHumanTool()])
    ctx = SkillContext(
        user_id="u2",
        user_profile=UserProfile(user_id="u2", name="Test"),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.new_session_state == "escalated"
    assert len(result.actions) == 2
    assert result.actions[0].tool_name == "pause_collection"
    assert result.actions[1].tool_name == "escalate_to_human"
    assert "抱歉" in result.response_text


@pytest.mark.asyncio
async def test_crisis_skill_is_one_way_door():
    skill = CrisisSkill()
    assert skill.is_one_way_door is True
    assert "CRISIS" in skill.triggers
    assert skill.name == "crisis_intervention"


@pytest.mark.asyncio
async def test_crisis_skill_executes_tools():
    skill = CrisisSkill(
        tools=[PauseCollectionTool(), WelfareAlertTool(), EscalateToHumanTool()]
    )
    ctx = SkillContext(
        user_id="u3",
        user_profile=UserProfile(user_id="u3", name="Test"),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.new_session_state == "crisis"
    assert len(result.actions) == 3
    assert result.actions[0].tool_name == "pause_collection"
    assert result.actions[1].tool_name == "welfare_alert"
    assert result.actions[2].tool_name == "escalate_to_human"
    assert "热线" in result.response_text


@pytest.mark.asyncio
async def test_stop_skill_is_one_way_door():
    skill = StopSkill()
    assert skill.is_one_way_door is True
    assert "STOP" in skill.triggers
    assert skill.name == "stop_handling"


@pytest.mark.asyncio
async def test_stop_skill_executes_tools():
    skill = StopSkill(tools=[AddToDncListTool(), PauseCollectionTool()])
    ctx = SkillContext(
        user_id="u4",
        user_profile=UserProfile(user_id="u4", name="Test"),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.new_session_state == "stopped"
    assert len(result.actions) == 2
    assert result.actions[0].tool_name == "add_to_dnc_list"
    assert result.actions[1].tool_name == "pause_collection"
    assert "停止" in result.response_text


@pytest.mark.asyncio
async def test_one_way_door_skills_with_missing_tools():
    """Skills should return ERROR when critical tools are missing."""
    skill = StopSkill(tools=[])
    ctx = SkillContext(
        user_id="u5",
        user_profile=UserProfile(user_id="u5", name="Test"),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.ERROR
    assert result.new_session_state == "stopped"
    assert "Critical tool" in result.thinking
