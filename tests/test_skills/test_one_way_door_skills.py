"""Tests for one-way door skills using SkillExecutor + ReActMockLLM."""

from __future__ import annotations

import pytest

from collect_agent.core.models import UserProfile
from collect_agent.skills.base import SkillContext, SkillResultStatus
from collect_agent.skills.complaint_skill import ComplaintSkill
from collect_agent.skills.crisis_skill import CrisisSkill
from collect_agent.skills.dispute_skill import DisputeSkill
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.stop_skill import StopSkill
from collect_agent.tools.compliance import (
    EscalateToHumanTool,
    PauseCollectionTool,
    WelfareAlertTool,
)
from collect_agent.tools.registry import ToolRegistry
from collect_agent.tools.user import AddToDncListTool
from tests.test_skills import ReActMockLLM


def _make_registry(tools: list) -> ToolRegistry:
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


def _make_ctx(user_id: str = "u1") -> SkillContext:
    return SkillContext(
        user_id=user_id,
        user_profile=UserProfile(user_id=user_id, name="Test"),
    )


# ─── DisputeSkill ───


@pytest.mark.asyncio
async def test_dispute_skill_is_one_way_door():
    skill = DisputeSkill()
    assert skill.is_one_way_door is True
    assert "D" in skill.triggers
    assert skill.name == "dispute_resolution"


@pytest.mark.asyncio
async def test_dispute_skill_react_executes_tools():
    """DisputeSkill: LLM calls pause_collection + escalate_to_human via ReAct."""
    skill = DisputeSkill(tools=[PauseCollectionTool(), EscalateToHumanTool()])
    llm = ReActMockLLM(
        actions=[
            """
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>pause_collection</name>
      <parameters>
        <user_id>u1</user_id>
        <days>7</days>
        <reason>dispute raised</reason>
      </parameters>
    </tool_call>
    <tool_call>
      <name>escalate_to_human</name>
      <parameters>
        <user_id>u1</user_id>
        <reason>bill dispute</reason>
      </parameters>
    </tool_call>
  </tool_calls>
</action>""",
            "<action><type>reply</type><text>我们已收到您的争议申请，将暂停催收并转人工核实。请保持电话畅通。</text></action>",
        ]
    )
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx()

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert len(result.actions) == 2
    assert result.actions[0].tool_name == "pause_collection"
    assert result.actions[0].result["status"] == "paused"
    assert result.actions[1].tool_name == "escalate_to_human"
    assert result.actions[1].result["status"] == "escalated"
    assert "争议" in result.response_text


# ─── ComplaintSkill ───


@pytest.mark.asyncio
async def test_complaint_skill_is_one_way_door():
    skill = ComplaintSkill()
    assert skill.is_one_way_door is True
    assert "E" in skill.triggers
    assert skill.name == "complaint_handling"


@pytest.mark.asyncio
async def test_complaint_skill_react_executes_tools():
    """ComplaintSkill: LLM pauses collection and escalates via ReAct."""
    skill = ComplaintSkill(tools=[PauseCollectionTool(), EscalateToHumanTool()])
    llm = ReActMockLLM(
        actions=[
            """
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>pause_collection</name>
      <parameters>
        <user_id>u2</user_id>
        <days>3</days>
        <reason>complaint received</reason>
      </parameters>
    </tool_call>
    <tool_call>
      <name>escalate_to_human</name>
      <parameters>
        <user_id>u2</user_id>
        <reason>user complaint</reason>
      </parameters>
    </tool_call>
  </tool_calls>
</action>""",
            "<action><type>reply</type><text>非常抱歉给您带来不好的体验，已为您暂停催收并安排专员处理。</text></action>",
        ]
    )
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u2")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert len(result.actions) == 2
    assert result.actions[0].tool_name == "pause_collection"
    assert result.actions[1].tool_name == "escalate_to_human"
    assert "抱歉" in result.response_text


# ─── CrisisSkill ───


@pytest.mark.asyncio
async def test_crisis_skill_is_one_way_door():
    skill = CrisisSkill()
    assert skill.is_one_way_door is True
    assert "CRISIS" in skill.triggers
    assert skill.name == "crisis_intervention"


@pytest.mark.asyncio
async def test_crisis_skill_react_executes_tools():
    """CrisisSkill: LLM triggers welfare alert and pauses collection via ReAct."""
    skill = CrisisSkill(
        tools=[PauseCollectionTool(), WelfareAlertTool(), EscalateToHumanTool()]
    )
    llm = ReActMockLLM(
        actions=[
            """
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>pause_collection</name>
      <parameters>
        <user_id>u3</user_id>
        <days>7</days>
        <reason>crisis intervention</reason>
      </parameters>
    </tool_call>
    <tool_call>
      <name>welfare_alert</name>
      <parameters>
        <user_id>u3</user_id>
        <details>User expressed suicidal ideation</details>
      </parameters>
    </tool_call>
    <tool_call>
      <name>escalate_to_human</name>
      <parameters>
        <user_id>u3</user_id>
        <reason>crisis - immediate attention needed</reason>
      </parameters>
    </tool_call>
  </tool_calls>
</action>""",
            "<action><type>reply</type><text>我们非常关心您的情况，已安排专业团队介入。请拨打心理援助热线：400-161-9995。</text></action>",
        ]
    )
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u3")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert len(result.actions) == 3
    assert result.actions[0].tool_name == "pause_collection"
    assert result.actions[1].tool_name == "welfare_alert"
    assert result.actions[1].result["notified_team"] == "welfare_support"
    assert result.actions[2].tool_name == "escalate_to_human"
    assert "热线" in result.response_text


# ─── StopSkill ───


@pytest.mark.asyncio
async def test_stop_skill_is_one_way_door():
    skill = StopSkill()
    assert skill.is_one_way_door is True
    assert "STOP" in skill.triggers
    assert skill.name == "stop_handling"


@pytest.mark.asyncio
async def test_stop_skill_react_executes_tools():
    """StopSkill: LLM adds to DNC and pauses collection via ReAct."""
    skill = StopSkill(tools=[AddToDncListTool(), PauseCollectionTool()])
    llm = ReActMockLLM(
        actions=[
            """
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>add_to_dnc_list</name>
      <parameters>
        <user_id>u4</user_id>
        <channel>all</channel>
      </parameters>
    </tool_call>
    <tool_call>
      <name>pause_collection</name>
      <parameters>
        <user_id>u4</user_id>
        <days>999999</days>
        <reason>user stop request</reason>
      </parameters>
    </tool_call>
  </tool_calls>
</action>""",
            "<action><type>reply</type><text>已为您办理停止联系，后续不再打扰。</text></action>",
        ]
    )
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u4")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert len(result.actions) == 2
    assert result.actions[0].tool_name == "add_to_dnc_list"
    assert result.actions[0].result["status"] == "added_to_dnc"
    assert result.actions[1].tool_name == "pause_collection"
    assert "停止" in result.response_text


# ─── Error Handling ───


@pytest.mark.asyncio
async def test_one_way_door_skills_with_missing_tools():
    """When tools are called but not registered, SkillExecutor records the error."""
    skill = StopSkill(tools=[])
    # LLM tries to call a tool that isn't registered
    llm = ReActMockLLM(
        actions=[
            """
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>add_to_dnc_list</name>
      <parameters>
        <user_id>u5</user_id>
        <channel>all</channel>
      </parameters>
    </tool_call>
  </tool_calls>
</action>""",
            "<action><type>reply</type><text>我已收到您的请求。</text></action>",
        ]
    )
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u5")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS  # LLM recovers and replies
    assert len(result.actions) == 1
    assert result.actions[0].tool_name == "add_to_dnc_list"
    assert "error" in result.actions[0].result
    assert "not found" in result.actions[0].result["error"]


@pytest.mark.asyncio
async def test_react_tool_call_with_invalid_params():
    """Tool parameter validation should catch invalid parameters."""
    skill = ComplaintSkill(tools=[PauseCollectionTool()])
    # LLM omits required 'reason' parameter
    llm = ReActMockLLM(
        actions=[
            """
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>pause_collection</name>
      <parameters>
        <user_id>u6</user_id>
        <days>3</days>
      </parameters>
    </tool_call>
  </tool_calls>
</action>""",
            "<action><type>reply</type><text>抱歉，操作遇到问题，已为您转接人工。</text></action>",
        ]
    )
    executor = SkillExecutor(llm_client=llm, tool_registry=_make_registry(skill.tools))
    ctx = _make_ctx(user_id="u6")

    result = await executor.execute(skill, ctx)

    assert result.status == SkillResultStatus.SUCCESS
    assert len(result.actions) == 1
    assert result.actions[0].tool_name == "pause_collection"
    assert "error" in result.actions[0].result
