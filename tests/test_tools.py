"""Tests for tool side effects (real, not mock)."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from collect_agent.core.models import UserProfile, UserState
from collect_agent.storage.memory_store import MemoryStore
from tests.conftest import MockStore


class TestQueryBill:
    @pytest.mark.asyncio
    async def test_query_bill(self):
        from collect_agent.tools.ops import query_bill

        store = MockStore()
        store.save(
            UserState(
                user_id="u1",
                profile=UserProfile(user_id="u1", amount_due=2580.0, overdue_days=10),
            )
        )

        result = await query_bill(user_id="u1", store=store)

        assert result["amount_due"] == 2580.0
        assert result["overdue_days"] == 10

    @pytest.mark.asyncio
    async def test_query_bill_user_not_found(self):
        from collect_agent.tools.ops import query_bill

        store = MockStore()
        result = await query_bill(user_id="missing", store=store)

        assert "error" in result


class TestPauseCollection:
    @pytest.mark.asyncio
    async def test_pause_collection(self):
        from collect_agent.tools.ops import pause_collection

        store = MockStore()
        store.save(
            UserState(user_id="u1", profile=UserProfile(user_id="u1"))
        )

        result = await pause_collection(
            user_id="u1", days=7, reason="user_complaint", store=store
        )

        assert result["status"] == "paused"
        assert result["reason"] == "user_complaint"

        # Verify state was actually updated
        state = store.load("u1")
        assert state.paused_until is not None
        assert state.paused_until > datetime.now()


class TestAddToDnc:
    @pytest.mark.asyncio
    async def test_add_to_dnc(self):
        from collect_agent.tools.ops import add_to_dnc

        store = MockStore()
        store.save(
            UserState(user_id="u1", profile=UserProfile(user_id="u1"))
        )

        result = await add_to_dnc(user_id="u1", reason="user_request", store=store)

        assert result["status"] == "added_to_dnc"

        # Verify DNC flag
        state = store.load("u1")
        assert hasattr(state, "dnc")


class TestEscalateToHuman:
    @pytest.mark.asyncio
    async def test_escalate_creates_ticket(self):
        from collect_agent.tools.ops import escalate_to_human

        store = MockStore()
        store.save(
            UserState(user_id="u1", profile=UserProfile(user_id="u1"))
        )

        result = await escalate_to_human(
            user_id="u1", reason="complaint", store=store
        )

        assert result["status"] == "escalated"
        assert "ticket_id" in result

        # Verify ticket was saved
        assert len(store.get_tickets()) == 1
        assert store.get_tickets()[0]["reason"] == "complaint"


class TestWelfareAlert:
    @pytest.mark.asyncio
    async def test_welfare_alert(self):
        from collect_agent.tools.ops import welfare_alert

        store = MockStore()

        result = await welfare_alert(
            user_id="u1", details="User expressed suicidal ideation", store=store
        )

        assert result["status"] == "alert_triggered"

        # Verify alert was saved
        assert len(store.get_alerts()) == 1
        assert store.get_alerts()[0]["notified_team"] == "welfare_support"


class TestScheduleReminder:
    @pytest.mark.asyncio
    async def test_schedule_reminder(self):
        from collect_agent.tools.ops import schedule_reminder

        store = MockStore()

        result = await schedule_reminder(
            user_id="u1",
            remind_date="2026-06-01T09:00:00Z",
            channel="sms",
            message="请记得还款",
            store=store,
        )

        assert result["status"] == "scheduled"

        # Verify reminder was saved
        assert len(store.get_reminders()) == 1
