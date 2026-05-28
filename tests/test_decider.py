"""Tests for Decider — intent recognition + skill selection."""

from __future__ import annotations

import pytest

from collect_agent.core.context import Context
from collect_agent.core.models import UserProfile
from collect_agent.decider import Decider
from collect_agent.intent.models import IntentCategory
from collect_agent.skills.base import Skill
from collect_agent.skills.registry import SkillRegistry
from tests.conftest import ReActMockLLM


@pytest.fixture
def skill_registry():
    reg = SkillRegistry()
    reg.register(Skill(name="negotiation", description="协商还款"))
    reg.register(Skill(name="complaint", description="投诉处理"))
    reg.register(Skill(name="stop", description="停止联系"))
    reg.register(Skill(name="crisis", description="危机干预"))
    reg.register(Skill(name="payment_guidance", description="还款引导"))
    reg.register(Skill(name="troubleshoot", description="故障排除"))
    return reg


@pytest.fixture
def decider(skill_registry):
    from tests.conftest import ReActMockLLM

    return Decider(
        llm_client=ReActMockLLM([]),
        skill_registry=skill_registry,
    )


@pytest.mark.asyncio
async def test_decide_cooperation(skill_registry):
    llm = ReActMockLLM([
        '{"intent": "COOPERATION", "selected_skill": "payment_guidance", "confidence": "high", "escalation": false, "emotion": "positive", "thinking": "用户明确表示还款意愿"}'
    ])
    decider = Decider(llm_client=llm, skill_registry=skill_registry)

    ctx = Context(
        user_message="我愿意还款，请问怎么操作？",
        profile=UserProfile(user_id="u1", name="张三"),
    )
    decision = await decider.decide(ctx)

    assert decision.intent == IntentCategory.COOPERATION
    assert decision.selected_skill == "payment_guidance"
    assert decision.confidence == "high"
    assert decision.escalation is False


@pytest.mark.asyncio
async def test_decide_negotiation(skill_registry):
    llm = ReActMockLLM([
        '{"intent": "NEGOTIATION", "selected_skill": "negotiation", "confidence": "medium", "escalation": false, "emotion": "negative", "thinking": "用户表示经济困难"}'
    ])
    decider = Decider(llm_client=llm, skill_registry=skill_registry)

    ctx = Context(
        user_message="我现在手头紧，能不能延期？",
        profile=UserProfile(user_id="u1"),
    )
    decision = await decider.decide(ctx)

    assert decision.intent == IntentCategory.NEGOTIATION
    assert decision.selected_skill == "negotiation"


@pytest.mark.asyncio
async def test_decide_complaint(skill_registry):
    llm = ReActMockLLM([
        '{"intent": "COMPLAINT", "selected_skill": "complaint", "confidence": "high", "escalation": true, "emotion": "angry", "thinking": "用户威胁投诉"}'
    ])
    decider = Decider(llm_client=llm, skill_registry=skill_registry)

    ctx = Context(
        user_message="你们再骚扰我我就去银保监会投诉",
        profile=UserProfile(user_id="u1"),
    )
    decision = await decider.decide(ctx)

    assert decision.intent == IntentCategory.COMPLAINT
    assert decision.escalation is True


@pytest.mark.asyncio
async def test_decide_fallback_when_skill_not_found(skill_registry):
    """When LLM selects a non-existent skill, fallback to intent-based mapping."""
    llm = ReActMockLLM([
        '{"intent": "NEGOTIATION", "selected_skill": "nonexistent", "confidence": "high", "escalation": false, "emotion": "neutral", "thinking": "test"}'
    ])
    decider = Decider(llm_client=llm, skill_registry=skill_registry)

    ctx = Context(
        user_message="test",
        profile=UserProfile(user_id="u1"),
    )
    decision = await decider.decide(ctx)

    # Should fallback to negotiation skill (which exists)
    assert decision.selected_skill == "negotiation"


@pytest.mark.asyncio
async def test_decide_parse_json_from_code_block(skill_registry):
    """LLM might wrap JSON in markdown code block."""
    llm = ReActMockLLM([
        'Some text before\n```json\n{"intent": "STOP", "selected_skill": "stop", "confidence": "high", "escalation": false, "emotion": "negative", "thinking": "test"}\n```\nSome text after'
    ])
    decider = Decider(llm_client=llm, skill_registry=skill_registry)

    ctx = Context(
        user_message="停止",
        profile=UserProfile(user_id="u1"),
    )
    decision = await decider.decide(ctx)

    assert decision.intent == IntentCategory.STOP


@pytest.mark.asyncio
async def test_decide_empty_registry():
    """When registry is empty, fallback still works."""
    empty_reg = SkillRegistry()
    llm = ReActMockLLM([
        '{"intent": "COOPERATION", "selected_skill": "payment_guidance", "confidence": "high", "escalation": false, "emotion": "neutral", "thinking": "test"}'
    ])
    decider = Decider(llm_client=llm, skill_registry=empty_reg)

    ctx = Context(
        user_message="test",
        profile=UserProfile(user_id="u1"),
    )
    decision = await decider.decide(ctx)

    assert decision.intent == IntentCategory.COOPERATION
    # Fallback mapping for cooperation -> payment_guidance
    assert decision.selected_skill == "payment_guidance"
