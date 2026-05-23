"""Tests for flowing-state skills using SkillExecutor + ReActMockLLM."""

from __future__ import annotations

import pytest

from src.core.models import UserProfile
from src.skills.base import SkillContext, SkillResultStatus
from src.skills.executor import SkillExecutor
from src.skills.followup_skill import FollowUpSkill
from src.skills.negotiation_skill import NegotiationSkill
from src.skills.onboard_skill import OnboardSkill
from src.skills.payment_guidance_skill import PaymentGuidanceSkill
from src.skills.reengage_skill import ReEngageSkill
from src.skills.troubleshoot_skill import TroubleshootSkill
from src.tools.billing import CreatePaymentPlanTool, QueryBillTool
from src.tools.messaging import SendMessageTool, SendPaymentLinkTool
from src.tools.promises import CheckPaymentStatusTool, RecordPromiseTool
from src.tools.registry import ToolRegistry
from src.tools.user import QueryUserHistoryTool, ScheduleReminderTool
from tests.test_skills import ReActMockLLM


def _make_registry(tools: list) -> ToolRegistry:
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


def _make_ctx(user_id: str = "u1", **kwargs) -> SkillContext:
    return SkillContext(
        user_id=user_id,
        user_profile=UserProfile(user_id=user_id, name="Test", amount_due=1000.0),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_onboard_skill_react_reply():
    """OnboardSkill: LLM replies directly without tool calls."""
    skill = OnboardSkill(tools=[QueryBillTool(), QueryUserHistoryTool(), SendMessageTool()])
    llm = ReActMockLLM(actions=[
        "<action><type>reply</type><text>Hello, we noticed your bill is overdue. Please contact us to settle.</text></action>"
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx()

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert "overdue" in result.response_text
    assert skill.is_one_way_door is False
    assert len(result.actions) == 0


@pytest.mark.asyncio
async def test_payment_guidance_skill_react_tool_then_reply():
    """PaymentGuidanceSkill: LLM calls query_bill then replies with guidance."""
    skill = PaymentGuidanceSkill(tools=[QueryBillTool(), SendPaymentLinkTool()])
    llm = ReActMockLLM(actions=[
        """<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>query_bill</name>
      <parameters><user_id>u2</user_id></parameters>
    </tool_call>
  </tool_calls>
</action>""",
        "<action><type>reply</type><text>您的账单金额为 2580 元，请点击链接还款。</text></action>"
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u2")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert "2580" in result.response_text
    assert len(result.actions) == 1
    assert result.actions[0].tool_name == "query_bill"
    assert result.actions[0].result["amount_due"] == 2580.00


@pytest.mark.asyncio
async def test_negotiation_skill_react_create_plan():
    """NegotiationSkill: LLM calls create_payment_plan then replies."""
    skill = NegotiationSkill(
        tools=[QueryBillTool(), CreatePaymentPlanTool(), RecordPromiseTool(), ScheduleReminderTool()]
    )
    llm = ReActMockLLM(actions=[
        """<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>create_payment_plan</name>
      <parameters>
        <user_id>u3</user_id>
        <installments>3</installments>
        <amount>2000</amount>
      </parameters>
    </tool_call>
  </tool_calls>
</action>""",
        "<action><type>reply</type><text>已为您生成分期方案，每期 666.67 元。</text></action>"
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u3", user_message="我现在没钱，能分期吗？")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert "分期" in result.response_text
    assert len(result.actions) == 1
    assert result.actions[0].tool_name == "create_payment_plan"
    assert result.actions[0].result["per_installment"] == 666.67


@pytest.mark.asyncio
async def test_reengage_skill_react_schedule_reminder():
    """ReEngageSkill: LLM schedules a reminder then replies."""
    skill = ReEngageSkill(tools=[QueryUserHistoryTool(), SendMessageTool(), ScheduleReminderTool()])
    llm = ReActMockLLM(actions=[
        """<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>schedule_reminder</name>
      <parameters>
        <user_id>u4</user_id>
        <remind_date>2025-04-20T09:00:00Z</remind_date>
        <channel>sms</channel>
        <message>Please remember to settle your bill.</message>
      </parameters>
    </tool_call>
  </tool_calls>
</action>""",
        "<action><type>reply</type><text>已为您安排后续提醒，请注意查收。</text></action>"
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u4")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert "提醒" in result.response_text
    assert len(result.actions) == 1
    assert result.actions[0].tool_name == "schedule_reminder"
    assert result.actions[0].result["status"] == "scheduled"


@pytest.mark.asyncio
async def test_troubleshoot_skill_react_reply():
    """TroubleshootSkill: LLM provides troubleshooting steps directly."""
    skill = TroubleshootSkill()
    llm = ReActMockLLM(actions=[
        "<action><type>reply</type><text>请尝试清除缓存后重新打开App。如果仍有问题，请联系技术支持。</text></action>"
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u5", user_message="App打不开")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert "缓存" in result.response_text
    assert skill.is_one_way_door is False


@pytest.mark.asyncio
async def test_followup_skill_react_check_payment():
    """FollowUpSkill: LLM checks payment status then replies."""
    skill = FollowUpSkill(tools=[CheckPaymentStatusTool(), QueryBillTool(), SendMessageTool()])
    llm = ReActMockLLM(actions=[
        """<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>check_payment_status</name>
      <parameters><user_id>u6</user_id></parameters>
    </tool_call>
  </tool_calls>
</action>""",
        "<action><type>reply</type><text>我们注意到您尚未完成还款，请尽快处理。</text></action>"
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u6")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert "尚未" in result.response_text
    assert len(result.actions) == 1
    assert result.actions[0].tool_name == "check_payment_status"
    assert result.actions[0].result["paid"] is False


@pytest.mark.asyncio
async def test_react_max_steps_fallback():
    """ReAct loop should return ERROR after max steps with no terminal action."""
    skill = PaymentGuidanceSkill(tools=[QueryBillTool()])
    # LLM keeps returning unknown actions, never reply/end/escalate
    llm = ReActMockLLM(actions=[
        "<action><type>thinking</type><text>I need to think more...</text></action>",
        "<action><type>thinking</type><text>Still thinking...</text></action>",
        "<action><type>thinking</type><text>Not done yet...</text></action>",
        "<action><type>thinking</type><text>Almost there...</text></action>",
        "<action><type>thinking</type><text>One more step...</text></action>",
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx()

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.ERROR
    assert "unable to complete" in result.response_text
    assert "Max ReAct steps" in result.thinking


@pytest.mark.asyncio
async def test_react_escalate_action():
    """LLM can return escalate action to trigger escalation."""
    skill = NegotiationSkill(tools=[])
    llm = ReActMockLLM(actions=[
        "<action><type>escalate</type><text>User is requesting a complex arrangement beyond my authority.</text></action>"
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx()

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.NEEDS_ESCALATION
    assert result.escalation is True
    assert "authority" in result.response_text


@pytest.mark.asyncio
async def test_react_end_action():
    """LLM can return end action to stop without responding."""
    skill = FollowUpSkill(tools=[])
    llm = ReActMockLLM(actions=[
        "<action><type>end</type></action>"
    ])
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx()

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.STOPPED
    assert result.response_text is None
    assert result.escalation is False
