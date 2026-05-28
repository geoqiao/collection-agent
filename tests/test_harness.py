"""Tests for Harness hard-rule guardrails."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserProfile, UserState
from collect_agent.harness import Harness


@pytest.fixture
def harness():
    return Harness()


def test_normal_user_not_blocked(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1"),
        session_state="normal",
    )
    event = Event(user_id="u1", type=EventType.USER_REPLIED, payload={"message": "我会还的"})
    result = harness.check(event, state)
    assert result.block is False


def test_resolved_user_blocked(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1"),
        session_state="resolved",
    )
    event = Event(user_id="u1", type=EventType.USER_REPLIED, payload={"message": "test"})
    result = harness.check(event, state)
    assert result.block is True
    assert result.reason == "already_resolved"


def test_stopped_user_blocked(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1"),
        session_state="stopped",
    )
    event = Event(user_id="u1", type=EventType.USER_REPLIED, payload={"message": "test"})
    result = harness.check(event, state)
    assert result.block is True
    assert result.reason == "user_stopped"


def test_paused_user_blocked(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1"),
        session_state="normal",
        paused_until=datetime.now(UTC) + timedelta(days=7),
    )
    event = Event(user_id="u1", type=EventType.USER_REPLIED, payload={"message": "test"})
    result = harness.check(event, state)
    assert result.block is True
    assert result.reason == "paused"


def test_paused_user_allowed_after_expiry(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1"),
        session_state="normal",
        paused_until=datetime.now(UTC) - timedelta(days=1),
    )
    event = Event(user_id="u1", type=EventType.USER_REPLIED, payload={"message": "test"})
    result = harness.check(event, state)
    assert result.block is False


def test_stop_keyword_forces_stop_intent(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1"),
        session_state="normal",
    )
    event = Event(user_id="u1", type=EventType.USER_REPLIED, payload={"message": "停止联系我"})
    result = harness.check(event, state)
    assert result.block is False
    assert result.force_intent is not None
    assert result.force_intent.value == "STOP"
    assert "stop_keyword" in result.reason


def test_crisis_keyword_forces_crisis_intent(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1"),
        session_state="normal",
    )
    event = Event(user_id="u1", type=EventType.USER_REPLIED, payload={"message": "我不想活了"})
    result = harness.check(event, state)
    assert result.block is False
    assert result.force_intent is not None
    assert result.force_intent.value == "CRISIS"
    assert "crisis_keyword" in result.reason


def test_sensitive_occupation_flagged(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1", occupation="律师"),
        session_state="normal",
    )
    event = Event(user_id="u1", type=EventType.USER_REPLIED, payload={"message": "test"})
    result = harness.check(event, state)
    assert result.block is False
    assert result.reason == "sensitive_occupation"


def test_outbound_event_not_blocked(harness):
    state = UserState(
        user_id="u1",
        profile=UserProfile(user_id="u1"),
        session_state="normal",
    )
    event = Event(user_id="u1", type=EventType.SCHEDULED_OUTREACH)
    result = harness.check(event, state)
    assert result.block is False
