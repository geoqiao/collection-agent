"""Tests for AgentSession v2 — Harness → Decide → Execute flow."""

from __future__ import annotations

import pytest

from collect_agent.agent.session import AgentSession
from collect_agent.compliance.checker import ComplianceChecker
from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserProfile, UserState
from collect_agent.decider import Decider
from collect_agent.harness import Harness
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.loader import SkillLoader
from collect_agent.skills.registry import SkillRegistry
from collect_agent.tools.registry import get_registry
from tests.conftest import MockStore, ReActMockLLM


@pytest.fixture
def agent_deps():
    """Create all dependencies for AgentSession."""
    store = MockStore()
    store.save(
        UserState(
            user_id="u1",
            profile=UserProfile(
                user_id="u1",
                name="张三",
                overdue_days=5,
                amount_due=1000.0,
            ),
            session_state="normal",
        )
    )

    skill_registry = SkillRegistry()
    for skill in SkillLoader().load_all():
        skill_registry.register(skill)

    harness = Harness()
    compliance = ComplianceChecker()
    tool_registry = get_registry()

    return {
        "store": store,
        "skill_registry": skill_registry,
        "harness": harness,
        "compliance": compliance,
        "tool_registry": tool_registry,
    }


def build_agent(agent_deps, llm_client):
    """Build an AgentSession with given LLM mock."""
    state = agent_deps["store"].load("u1")
    decider = Decider(
        llm_client=llm_client,
        skill_registry=agent_deps["skill_registry"],
    )
    skill_executor = SkillExecutor(
        llm_client=llm_client,
        tool_registry=agent_deps["tool_registry"],
    )

    return AgentSession(
        user_id="u1",
        user_state=state,
        skill_registry=agent_deps["skill_registry"],
        skill_executor=skill_executor,
        decider=decider,
        harness=agent_deps["harness"],
        compliance_checker=agent_deps["compliance"],
        storage=agent_deps["store"],
    )


class TestAgentSessionFlow:
    @pytest.mark.asyncio
    async def test_user_replied_cooperation(self, agent_deps):
        """User expresses willingness to pay → payment_guidance skill → reply."""
        llm = ReActMockLLM([
            # Decider: intent + skill selection
            '{"intent": "COOPERATION", "selected_skill": "payment_guidance", "confidence": "high", "escalation": false, "emotion": "positive", "thinking": "用户愿意还款"}',
            # Executor: direct reply
            '{"type": "reply", "thinking": "引导还款", "text": "感谢您的配合，请点击以下链接完成还款。"}',
        ])
        agent = build_agent(agent_deps, llm)

        event = Event(
            user_id="u1",
            type=EventType.USER_REPLIED,
            payload={"message": "我愿意还款"},
        )
        result = await agent.handle_event(event)

        assert result.status == "success"
        assert "还款" in result.response_text
        assert agent.user_state.session_state == "normal"
        # Conversation recorded
        assert len(agent.user_state.conversation.messages) == 2  # inbound + outbound

    @pytest.mark.asyncio
    async def test_user_replied_stop_keyword(self, agent_deps):
        """User says STOP → harness intercepts → fixed template via stop skill."""
        # Decider is bypassed (harness forces intent), but Executor still runs
        llm = ReActMockLLM([
            '{"type": "tool_call", "thinking": "加入DNC", "name": "add_to_dnc", "parameters": {"user_id": "u1", "reason": "user_stop"}}',
            '{"type": "reply", "thinking": "确认", "text": "已收到您的要求，立即停止联系。"}',
        ])
        agent = build_agent(agent_deps, llm)

        event = Event(
            user_id="u1",
            type=EventType.USER_REPLIED,
            payload={"message": "停止联系我"},
        )
        result = await agent.handle_event(event)

        assert result.status == "success"
        assert "停止" in result.response_text or "已收到" in result.response_text
        assert agent.user_state.session_state == "stopped"

    @pytest.mark.asyncio
    async def test_user_replied_crisis_keyword(self, agent_deps):
        """User expresses crisis → harness intercepts → crisis skill."""
        llm = ReActMockLLM([
            # Executor: crisis skill tools + reply
            '{"type": "tool_call", "thinking": "暂停催收", "name": "pause_collection", "parameters": {"user_id": "u1", "days": 30, "reason": "crisis"}}',
            '{"type": "tool_call", "thinking": "告警", "name": "welfare_alert", "parameters": {"user_id": "u1", "details": "suicidal ideation"}}',
            '{"type": "reply", "thinking": "安慰", "text": "我们非常关心您，请拨打心理援助热线 400-161-9995。"}',
        ])
        agent = build_agent(agent_deps, llm)

        event = Event(
            user_id="u1",
            type=EventType.USER_REPLIED,
            payload={"message": "我不想活了"},
        )
        result = await agent.handle_event(event)

        assert result.status == "success"
        assert "热线" in result.response_text or "400" in result.response_text
        assert agent.user_state.session_state == "crisis"
        # Verify pause_collection side effect
        assert agent_deps["store"].load("u1").paused_until is not None
        # Verify welfare alert
        assert len(agent_deps["store"].get_alerts()) == 1

    @pytest.mark.asyncio
    async def test_sensitive_occupation_routing(self, agent_deps):
        """Sensitive occupation user → standard skill (harness flagged)."""
        # Update user to sensitive occupation
        agent_deps["store"].save(
            UserState(
                user_id="u2",
                profile=UserProfile(
                    user_id="u2",
                    name="李律师",
                    occupation="律师",
                    overdue_days=5,
                    amount_due=1000.0,
                ),
                session_state="normal",
            )
        )

        llm = ReActMockLLM([
            # Decider for standard skill
            '{"intent": "COOPERATION", "selected_skill": "standard", "confidence": "high", "escalation": false, "emotion": "neutral", "thinking": "敏感职业"}',
            # Executor: standard reply
            '{"type": "reply", "thinking": "标准提醒", "text": "您好，您的账单已逾期5天，请尽快处理。"}',
        ])

        state = agent_deps["store"].load("u2")
        decider = Decider(llm_client=llm, skill_registry=agent_deps["skill_registry"])
        executor = SkillExecutor(llm_client=llm, tool_registry=agent_deps["tool_registry"])

        agent = AgentSession(
            user_id="u2",
            user_state=state,
            skill_registry=agent_deps["skill_registry"],
            skill_executor=executor,
            decider=decider,
            harness=agent_deps["harness"],
            compliance_checker=agent_deps["compliance"],
            storage=agent_deps["store"],
        )

        event = Event(
            user_id="u2",
            type=EventType.USER_REPLIED,
            payload={"message": "我会处理的"},
        )
        result = await agent.handle_event(event)

        assert result.status == "success"
        # Should NOT contain negotiation keywords
        assert "分期" not in result.response_text
        assert "协商" not in result.response_text

    @pytest.mark.asyncio
    async def test_scheduled_outreach(self, agent_deps):
        """System-initiated outreach → onboard skill."""
        llm = ReActMockLLM([
            # Decider
            '{"intent": "COOPERATION", "selected_skill": "onboard", "confidence": "medium", "escalation": false, "emotion": "neutral", "thinking": "首次触达"}',
            # Executor
            '{"type": "reply", "thinking": "首次联系", "text": "您好，您的账单已逾期，请尽快处理。"}',
        ])
        agent = build_agent(agent_deps, llm)

        event = Event(user_id="u1", type=EventType.SCHEDULED_OUTREACH)
        result = await agent.handle_event(event)

        assert result.status == "success"
        assert "账单" in result.response_text or "逾期" in result.response_text

    @pytest.mark.asyncio
    async def test_locked_state_fixed_template(self, agent_deps):
        """When session is locked (e.g., stopped), always return fixed template."""
        agent_deps["store"].save(
            UserState(
                user_id="u1",
                profile=UserProfile(user_id="u1"),
                session_state="stopped",
            )
        )

        llm = ReActMockLLM([])  # Should not be called
        agent = build_agent(agent_deps, llm)

        event = Event(
            user_id="u1",
            type=EventType.USER_REPLIED,
            payload={"message": "test"},
        )
        result = await agent.handle_event(event)

        assert result.status == "blocked"
        assert llm.call_count == 0

    @pytest.mark.asyncio
    async def test_compliance_audit_blocks_forbidden_words(self, agent_deps):
        """If LLM generates forbidden words, audit blocks and returns fallback."""
        llm = ReActMockLLM([
            # Decider
            '{"intent": "COOPERATION", "selected_skill": "payment_guidance", "confidence": "high", "escalation": false, "emotion": "neutral", "thinking": "test"}',
            # Executor: generates forbidden word
            '{"type": "reply", "thinking": "bad", "text": "不还款我们就法律诉讼。"}',
        ])
        agent = build_agent(agent_deps, llm)

        event = Event(
            user_id="u1",
            type=EventType.USER_REPLIED,
            payload={"message": "test"},
        )
        result = await agent.handle_event(event)

        assert result.status == "error"
        assert "法律诉讼" not in result.response_text  # Blocked
        assert "客服热线" in result.response_text  # Fallback
