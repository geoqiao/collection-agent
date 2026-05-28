"""Tests for SkillLoader and SkillExecutor."""

from __future__ import annotations

import pytest
from pathlib import Path

from collect_agent.core.context import Context
from collect_agent.core.models import UserProfile, UserState
from collect_agent.skills.base import Skill, SkillResult
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.loader import SkillLoader
from collect_agent.skills.registry import SkillRegistry
from collect_agent.tools.registry import ToolRegistry, get_registry
from tests.conftest import ReActMockLLM


# --- SkillLoader tests ---


class TestSkillLoader:
    def test_load_from_frontmatter(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            """---
name: test_skill
description: A test skill for unit testing
tools: [tool_a, tool_b]
max_steps: 5
---

# Test Skill

Some instructions here.
""",
            encoding="utf-8",
        )
        loader = SkillLoader(skills_dir=tmp_path)
        skills = loader.load_all()

        assert len(skills) == 1
        skill = skills[0]
        assert skill.name == "test_skill"
        assert skill.description == "A test skill for unit testing"
        assert skill.tools == ["tool_a", "tool_b"]
        assert skill.max_steps == 5
        assert "Some instructions here" in skill.content

    def test_load_without_frontmatter(self, tmp_path):
        md = tmp_path / "legacy.md"
        md.write_text(
            """# Legacy Skill

This is a legacy skill without frontmatter.
""",
            encoding="utf-8",
        )
        loader = SkillLoader(skills_dir=tmp_path)
        skills = loader.load_all()

        assert len(skills) == 1
        assert skills[0].name == "legacy_skill"
        assert "legacy skill without frontmatter" in skills[0].description

    def test_load_empty_dir(self, tmp_path):
        loader = SkillLoader(skills_dir=tmp_path)
        skills = loader.load_all()
        assert skills == []

    def test_get_system_prompt(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            """---
name: test
description: desc
tools: [t1]
---

# Instructions

Do this and that.
""",
            encoding="utf-8",
        )
        loader = SkillLoader(skills_dir=tmp_path)
        skill = loader.load_all()[0]
        prompt = skill.get_system_prompt()

        assert "# Skill: test" in prompt
        assert "desc" in prompt
        assert "t1" in prompt
        assert "Do this and that" in prompt


# --- SkillExecutor tests ---


@pytest.fixture
def tool_registry():
    """Fresh tool registry for each test."""
    reg = ToolRegistry()
    from collect_agent.tools.ops import query_bill, pause_collection

    # Manually register for test isolation
    reg.register(query_bill._tool_info)
    reg.register(pause_collection._tool_info)
    return reg


class TestSkillExecutor:
    @pytest.mark.asyncio
    async def test_reply_action(self, tool_registry):
        llm = ReActMockLLM([
            '{"type": "reply", "thinking": "用户问怎么还款", "text": "请点击以下链接还款。"}'
        ])
        executor = SkillExecutor(llm_client=llm, tool_registry=tool_registry)
        skill = Skill(name="payment", description="引导还款", tools=[], max_steps=3)
        ctx = Context(user_message="怎么还款？", profile=UserProfile(user_id="u1"))

        result = await executor.execute(skill, ctx, None)

        assert result.status == "success"
        assert result.response_text == "请点击以下链接还款。"
        assert result.thinking == "用户问怎么还款"

    @pytest.mark.asyncio
    async def test_tool_call_then_reply(self, tool_registry):
        from tests.conftest import MockStore

        store = MockStore()
        store.save(
            UserState(
                user_id="u1",
                profile=UserProfile(user_id="u1", name="张三", amount_due=1000.0, overdue_days=5),
            )
        )

        llm = ReActMockLLM([
            '{"type": "tool_call", "thinking": "先查账单", "name": "query_bill", "parameters": {"user_id": "u1"}}',
            '{"type": "reply", "thinking": "已查到", "text": "您的账单是1000元。"}'
        ])
        executor = SkillExecutor(llm_client=llm, tool_registry=tool_registry)
        skill = Skill(name="test", description="test", tools=["query_bill"], max_steps=3)
        ctx = Context(user_message="多少钱？", profile=UserProfile(user_id="u1"))

        result = await executor.execute(skill, ctx, store)

        assert result.status == "success"
        assert "1000" in result.response_text
        assert llm.call_count == 2

    @pytest.mark.asyncio
    async def test_escalate_action(self, tool_registry):
        llm = ReActMockLLM([
            '{"type": "escalate", "thinking": "需要人工", "text": "已为您转接人工。"}'
        ])
        executor = SkillExecutor(llm_client=llm, tool_registry=tool_registry)
        skill = Skill(name="complaint", description="投诉", tools=[], max_steps=3)
        ctx = Context(user_message="我要投诉", profile=UserProfile(user_id="u1"))

        result = await executor.execute(skill, ctx, None)

        assert result.status == "needs_escalation"
        assert result.escalation is True
        assert result.new_session_state == "escalated"

    @pytest.mark.asyncio
    async def test_max_steps_reached(self, tool_registry):
        """When LLM never returns reply/escalate, return error after max_steps."""
        llm = ReActMockLLM([
            '{"type": "thinking", "thinking": "hmm"}',
            '{"type": "thinking", "thinking": "still thinking"}',
            '{"type": "thinking", "thinking": "more thinking"}',
        ])
        executor = SkillExecutor(llm_client=llm, tool_registry=tool_registry)
        skill = Skill(name="test", description="test", tools=[], max_steps=3)
        ctx = Context(user_message="test", profile=UserProfile(user_id="u1"))

        result = await executor.execute(skill, ctx, None)

        assert result.status == "error"
        assert "系统繁忙" in result.response_text
        assert "Max ReAct steps" in result.thinking

    @pytest.mark.asyncio
    async def test_tool_not_found(self, tool_registry):
        """When tool is not registered, record error but continue."""
        llm = ReActMockLLM([
            '{"type": "tool_call", "thinking": "call missing tool", "name": "nonexistent", "parameters": {}}',
            '{"type": "reply", "thinking": "fallback", "text": "抱歉，操作遇到问题。"}'
        ])
        executor = SkillExecutor(llm_client=llm, tool_registry=tool_registry)
        skill = Skill(name="test", description="test", tools=[], max_steps=3)
        ctx = Context(user_message="test", profile=UserProfile(user_id="u1"))

        result = await executor.execute(skill, ctx, None)

        assert result.status == "success"
        assert "抱歉" in result.response_text
