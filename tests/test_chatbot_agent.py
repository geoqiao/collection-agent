"""Tests for ChatbotAgent."""

from __future__ import annotations

import pytest

from collect_agent.chatbot.agent import ChatbotAgent, ChatContext
from collect_agent.core.models import UserProfile
from collect_agent.intent.models import (
    ConfidenceLevel,
    EmotionLevel,
    IntentCategory,
    IntentResult,
)
from collect_agent.llm.base import LLMClient, LLMResponse
from collect_agent.prompts.engine import PromptEngine
from collect_agent.skills.base import SkillResult, SkillResultStatus
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.registry import SkillRegistry


class MockLLMClient(LLMClient):
    async def chat(self, messages, temperature=0.7, max_tokens=1024):
        return LLMResponse(content="mock")

    async def detect_intent(self, user_message: str, context: dict) -> str:
        return "cooperation"

    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        return "mock response"


class MockSkillExecutor(SkillExecutor):
    def __init__(self):
        pass

    async def execute(self, skill, ctx):
        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="mock skill response",
            thinking="mock",
        )


class MockIntentRecognizer:
    async def recognize(self, user_message, context):
        return IntentResult(
            category=IntentCategory.COOPERATION,
            confidence=ConfidenceLevel.HIGH,
            escalation=False,
            emotion=EmotionLevel.NEUTRAL,
            reasoning="mock",
        )

    async def recognize_with_guardrails(self, user_message, session_state):
        return IntentResult(
            category=IntentCategory.COOPERATION,
            confidence=ConfidenceLevel.HIGH,
            escalation=False,
            emotion=EmotionLevel.NEUTRAL,
            reasoning="mock guardrail",
        )


@pytest.mark.asyncio
async def test_one_way_door_state_returns_fixed_template():
    agent = ChatbotAgent(
        llm_client=MockLLMClient(),
        skill_executor=MockSkillExecutor(),
        intent_recognizer=MockIntentRecognizer(),
        prompt_engine=PromptEngine(),
    )
    for state in ["escalated", "stopped", "crisis", "disputed"]:
        ctx = ChatContext(
            user_id="u1",
            user_profile=UserProfile(user_id="u1", name="Test"),
            session_state=state,
        )
        result = await agent.handle_message("u1", "test", ctx)
        assert result.message == ChatbotAgent.FIXED_TEMPLATES[state]
        assert result.new_session_state == state


@pytest.mark.asyncio
async def test_one_way_door_intent_returns_fixed_template():
    class CrisisRecognizer(MockIntentRecognizer):
        async def recognize(self, user_message, context):
            return IntentResult(
                category=IntentCategory.CRISIS,
                confidence=ConfidenceLevel.HIGH,
                escalation=True,
                emotion=EmotionLevel.NEGATIVE,
                reasoning="crisis detected",
            )

    agent = ChatbotAgent(
        llm_client=MockLLMClient(),
        skill_executor=MockSkillExecutor(),
        intent_recognizer=CrisisRecognizer(),
        prompt_engine=PromptEngine(),
    )
    ctx = ChatContext(
        user_id="u1",
        user_profile=UserProfile(user_id="u1", name="Test"),
        session_state="normal",
    )
    result = await agent.handle_message("u1", "不想活了", ctx)
    assert "热线" in result.message
    assert result.new_session_state == "crisis"
    assert result.escalation is True


@pytest.mark.asyncio
async def test_normal_intent_with_skill_registry():
    from collect_agent.skills.onboard_skill import OnboardSkill

    registry = SkillRegistry()
    registry.register(OnboardSkill())

    agent = ChatbotAgent(
        llm_client=MockLLMClient(),
        skill_executor=MockSkillExecutor(),
        intent_recognizer=MockIntentRecognizer(),
        prompt_engine=PromptEngine(),
        skill_registry=registry,
    )
    ctx = ChatContext(
        user_id="u1",
        user_profile=UserProfile(user_id="u1", name="Test"),
        session_state="normal",
    )
    result = await agent.handle_message("u1", "test", ctx)
    assert result.message is not None
    assert result.intent == "A"
