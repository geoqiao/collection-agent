"""Tests for AgentSession."""

from __future__ import annotations

import pytest

from collect_agent.agent.session import AgentSession
from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserProfile, UserState
from collect_agent.intent.models import (
    ConfidenceLevel,
    EmotionLevel,
    IntentCategory,
    IntentResult,
)
from collect_agent.intent.recognizer import IntentRecognizer
from collect_agent.llm.base import LLMClient, LLMResponse
from collect_agent.prompts.engine import PromptEngine
from collect_agent.session.enhanced_state_machine import StateMachine
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.onboard_skill import OnboardSkill
from collect_agent.skills.payment_guidance_skill import PaymentGuidanceSkill
from collect_agent.skills.registry import SkillRegistry
from collect_agent.tools.registry import ToolRegistry
from collect_agent.storage.memory_store import MemoryStore


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
        from collect_agent.skills.base import SkillResult, SkillResultStatus

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="mock response",
            thinking="mock",
        )


class MockIntentRecognizer(IntentRecognizer):
    def __init__(self):
        pass

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


class MockComplianceChecker:
    def is_within_valid_hours(self, t=None):
        return True

    def has_forbidden_words(self, content):
        return False

    def audit_content(self, content):
        return True, ""


def create_session(state="normal"):
    user_state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1", name="Test"),
        session_state=state,
    )
    registry = SkillRegistry()
    registry.register(OnboardSkill())
    registry.register(PaymentGuidanceSkill())
    return AgentSession(
        user_id="u1",
        user_state=user_state,
        skill_registry=registry,
        intent_recognizer=MockIntentRecognizer(),
        state_machine=StateMachine(),
        skill_executor=MockSkillExecutor(),
        tool_registry=ToolRegistry(),
        prompt_engine=PromptEngine(),
        llm_client=MockLLMClient(),
        storage=MemoryStore(),
        compliance_checker=MockComplianceChecker(),
    )


@pytest.mark.asyncio
async def test_handle_user_replied():
    session = create_session()
    event = Event(
        user_id="u1",
        type=EventType.USER_REPLIED,
        payload={"message": "我想还款"},
    )
    result = await session.handle_event(event)
    assert result is not None
    assert result.status == "success"


@pytest.mark.asyncio
async def test_handle_scheduled_outreach():
    session = create_session()
    event = Event(
        user_id="u1",
        type=EventType.SCHEDULED_OUTREACH,
        payload={},
    )
    result = await session.handle_event(event)
    assert result is not None
    assert result.status == "success"  # OnboardSkill is registered


@pytest.mark.asyncio
async def test_handle_payment_success():
    session = create_session()
    event = Event(
        user_id="u1",
        type=EventType.USER_PAYMENT_SUCCESS,
        payload={},
    )
    result = await session.handle_event(event)
    assert result is not None
    assert result.status == "success"
    assert result.new_session_state == "resolved"
    assert session.state_machine.current.value == "resolved"


@pytest.mark.asyncio
async def test_one_way_door_locked():
    from collect_agent.session.enhanced_state_machine import AgentSessionState

    session = create_session()
    session.state_machine.transition(AgentSessionState.ESCALATED)
    event = Event(
        user_id="u1",
        type=EventType.USER_REPLIED,
        payload={"message": "test"},
    )
    result = await session.handle_event(event)
    assert result is not None
    assert result.status == "success"
    assert result.new_session_state == "escalated"
    assert "抱歉" in result.response_text


@pytest.mark.asyncio
async def test_silence_timeout():
    session = create_session()
    event = Event(
        user_id="u1",
        type=EventType.SILENCE_TIMEOUT,
        payload={},
    )
    result = await session.handle_event(event)
    assert result is not None
