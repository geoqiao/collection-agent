"""Tests for flowing-state skills."""

from __future__ import annotations

import pytest

from src.core.models import UserProfile
from src.skills.base import SkillContext, SkillResultStatus
from src.skills.followup_skill import FollowUpSkill
from src.skills.negotiation_skill import NegotiationSkill
from src.skills.onboard_skill import OnboardSkill
from src.skills.payment_guidance_skill import PaymentGuidanceSkill
from src.skills.reengage_skill import ReEngageSkill
from src.skills.troubleshoot_skill import TroubleshootSkill
from src.tools.billing import CreatePaymentPlanTool, QueryBillTool
from src.tools.messaging import SendMessageTool, SendPaymentLinkTool
from src.tools.promises import CheckPaymentStatusTool, RecordPromiseTool
from src.tools.user import QueryUserHistoryTool, ScheduleReminderTool


@pytest.mark.asyncio
async def test_onboard_skill():
    skill = OnboardSkill(tools=[QueryBillTool(), QueryUserHistoryTool(), SendMessageTool()])
    ctx = SkillContext(
        user_id="u1",
        user_profile=UserProfile(user_id="u1", name="Test", amount_due=1000.0),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.response_text is not None
    assert skill.is_one_way_door is False


@pytest.mark.asyncio
async def test_payment_guidance_skill():
    skill = PaymentGuidanceSkill(tools=[QueryBillTool(), SendPaymentLinkTool()])
    ctx = SkillContext(
        user_id="u2",
        user_profile=UserProfile(user_id="u2", name="Test", amount_due=500.0),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.response_text is not None
    assert skill.is_one_way_door is False


@pytest.mark.asyncio
async def test_negotiation_skill():
    skill = NegotiationSkill(
        tools=[QueryBillTool(), CreatePaymentPlanTool(), RecordPromiseTool(), ScheduleReminderTool()]
    )
    ctx = SkillContext(
        user_id="u3",
        user_profile=UserProfile(user_id="u3", name="Test", amount_due=2000.0),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.response_text is not None
    assert skill.is_one_way_door is False


@pytest.mark.asyncio
async def test_reengage_skill():
    skill = ReEngageSkill(tools=[QueryUserHistoryTool(), SendMessageTool(), ScheduleReminderTool()])
    ctx = SkillContext(
        user_id="u4",
        user_profile=UserProfile(user_id="u4", name="Test"),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.response_text is not None
    assert skill.is_one_way_door is False


@pytest.mark.asyncio
async def test_troubleshoot_skill():
    skill = TroubleshootSkill()
    ctx = SkillContext(
        user_id="u5",
        user_profile=UserProfile(user_id="u5", name="Test"),
        user_message="App打不开",
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.response_text is not None
    assert len(result.response_text) > 0
    assert skill.is_one_way_door is False


@pytest.mark.asyncio
async def test_followup_skill_paid():
    skill = FollowUpSkill(tools=[CheckPaymentStatusTool(), QueryBillTool(), SendMessageTool()])
    ctx = SkillContext(
        user_id="u6",
        user_profile=UserProfile(user_id="u6", name="Test"),
    )
    result = await skill.execute(ctx)
    assert result.status == SkillResultStatus.SUCCESS
    assert result.response_text is not None
    assert skill.is_one_way_door is False
