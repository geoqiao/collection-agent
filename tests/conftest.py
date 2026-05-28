"""Shared test fixtures and utilities."""

from __future__ import annotations

import pytest

from collect_agent.core.models import UserProfile, UserState
from collect_agent.storage.memory_store import MemoryStore


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def user_state():
    return UserState(
        user_id="u001",
        profile=UserProfile(
            user_id="u001",
            name="张三",
            overdue_days=5,
            amount_due=1000.0,
            occupation=None,
        ),
        session_state="normal",
    )


@pytest.fixture
def saved_user(store, user_state):
    store.save(user_state)
    return user_state


class MockStore:
    """Store that tracks side effects for testing."""

    def __init__(self):
        self._states: dict[str, UserState] = {}
        self._tickets: list[dict] = []
        self._alerts: list[dict] = []
        self._promises: list[dict] = []
        self._reminders: list[dict] = []

    def save(self, state: UserState) -> None:
        self._states[state.user_id] = state

    def load(self, user_id: str) -> UserState | None:
        return self._states.get(user_id)

    async def save_ticket(self, ticket: dict) -> None:
        self._tickets.append(ticket)

    async def save_alert(self, alert: dict) -> None:
        self._alerts.append(alert)

    async def save_promise(self, promise: dict) -> None:
        self._promises.append(promise)

    async def save_reminder(self, reminder: dict) -> None:
        self._reminders.append(reminder)

    def get_tickets(self) -> list[dict]:
        return self._tickets

    def get_alerts(self) -> list[dict]:
        return self._alerts

    def get_promises(self) -> list[dict]:
        return self._promises

    def get_reminders(self) -> list[dict]:
        return self._reminders


class ReActMockLLM:
    """Mock LLM that returns pre-configured responses for ReAct testing."""

    def __init__(self, responses: list[str]):
        self._responses = responses
        self._call_count = 0

    async def chat(self, messages, temperature=0.7, max_tokens=1024, **kwargs):
        from collect_agent.llm.base import LLMResponse

        idx = min(self._call_count, len(self._responses) - 1)
        content = self._responses[idx]
        self._call_count += 1
        return LLMResponse(content=content)

    @property
    def call_count(self) -> int:
        return self._call_count
