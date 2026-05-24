import os
import tempfile
from datetime import datetime

import pytest

from collect_agent.core.models import (
    ConversationContext,
    Message,
    UserProfile,
    UserState,
)
from collect_agent.quota.usage import DailyQuotaUsage, QuotaStorage
from collect_agent.storage.memory_store import MemoryStore
from collect_agent.storage.sqlite_store import SQLiteStore


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def sample_state():
    return UserState(user_id="u001", profile=UserProfile(user_id="u001", name="张三"))


def test_save_and_load(store, sample_state):
    store.save(sample_state)
    loaded = store.load("u001")
    assert loaded is not None
    assert loaded.user_id == "u001"
    assert loaded.profile.name == "张三"


def test_load_nonexistent(store):
    assert store.load("nonexistent") is None


def test_load_all(store, sample_state):
    store.save(sample_state)
    store.save(
        UserState(user_id="u002", profile=UserProfile(user_id="u002", name="李四"))
    )
    all_states = store.load_all()
    assert len(all_states) == 2


# --- SQLiteStore tests ---


@pytest.fixture
def sqlite_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = SQLiteStore(db_path=path)
    yield store
    os.unlink(path)


def test_sqlite_save_and_load(sqlite_store):
    state = UserState(
        user_id="u001",
        profile=UserProfile(
            user_id="u001",
            name="张三",
            phone="13800138000",
            occupation="工程师",
            overdue_days=5,
            amount_due=1000.0,
        ),
        session_state="active",
        channel_states={"sms": "sent", "call": "answered"},
        conversation=ConversationContext(
            messages=[
                Message(
                    channel="sms",
                    direction="outbound",
                    content="hello",
                    timestamp=datetime(2024, 1, 1, 12, 0, 0),
                )
            ],
            current_intent="greeting",
            negotiation_round=1,
        ),
        quota_usage={"calls": 3, "sms": 2},
    )
    sqlite_store.save(state)
    loaded = sqlite_store.load("u001")
    assert loaded is not None
    assert loaded.user_id == "u001"
    assert loaded.profile.name == "张三"
    assert loaded.profile.phone == "13800138000"
    assert loaded.profile.occupation == "工程师"
    assert loaded.profile.overdue_days == 5
    assert loaded.profile.amount_due == 1000.0
    assert loaded.session_state == "active"
    assert loaded.channel_states == {"sms": "sent", "call": "answered"}
    assert loaded.conversation.current_intent == "greeting"
    assert loaded.conversation.negotiation_round == 1
    assert len(loaded.conversation.messages) == 1
    msg = loaded.conversation.messages[0]
    assert msg.channel == "sms"
    assert msg.direction == "outbound"
    assert msg.content == "hello"
    assert msg.timestamp == datetime(2024, 1, 1, 12, 0, 0)
    assert loaded.quota_usage == {"calls": 3, "sms": 2}


def test_sqlite_load_all(sqlite_store):
    sqlite_store.save(
        UserState(user_id="u001", profile=UserProfile(user_id="u001", name="张三"))
    )
    sqlite_store.save(
        UserState(user_id="u002", profile=UserProfile(user_id="u002", name="李四"))
    )
    all_states = sqlite_store.load_all()
    assert len(all_states) == 2
    ids = {s.user_id for s in all_states}
    assert ids == {"u001", "u002"}


def test_sqlite_delete(sqlite_store):
    state = UserState(user_id="u001", profile=UserProfile(user_id="u001", name="张三"))
    sqlite_store.save(state)
    assert sqlite_store.load("u001") is not None
    sqlite_store.delete("u001")
    assert sqlite_store.load("u001") is None


def test_sqlite_json_serialization(sqlite_store):
    state = UserState(
        user_id="u001",
        profile=UserProfile(user_id="u001", name="张三"),
        channel_states={"sms": "sent"},
        conversation=ConversationContext(
            messages=[
                Message(
                    channel="sms",
                    direction="outbound",
                    content="hello",
                    timestamp=datetime(2024, 1, 1, 12, 0, 0),
                )
            ],
        ),
        quota_usage={"calls": 1},
    )
    sqlite_store.save(state)
    loaded = sqlite_store.load("u001")
    assert loaded.channel_states == {"sms": "sent"}
    assert loaded.conversation.messages[0].content == "hello"
    assert loaded.quota_usage == {"calls": 1}


def test_sqlite_schema_auto_creation():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        assert os.path.exists(path)
        store = SQLiteStore(db_path=path)
        # Verify table exists by saving and loading
        state = UserState(
            user_id="u001", profile=UserProfile(user_id="u001", name="张三")
        )
        store.save(state)
        assert store.load("u001") is not None
    finally:
        os.unlink(path)


def test_sqlite_context_manager():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        with SQLiteStore(db_path=path) as store:
            state = UserState(
                user_id="u001", profile=UserProfile(user_id="u001", name="张三")
            )
            store.save(state)
            assert store.load("u001") is not None
        # After exiting context manager, connection is closed
    finally:
        if os.path.exists(path):
            os.unlink(path)


# --- QuotaStorage tests ---


@pytest.fixture
def quota_storage():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    storage = QuotaStorage(db_path=path)
    yield storage
    os.unlink(path)


def test_quota_save_and_load(quota_storage):
    usage = DailyQuotaUsage(
        user_id="u001",
        date="2024-01-01",
        call_self_count=2,
        call_contact_count=1,
        call_answered_count=1,
        call_last_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        call_timestamps=[datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 10, 0, 0)],
        chat_sent_count=5,
        chat_user_replied=True,
        chat_last_timestamp=datetime(2024, 1, 1, 11, 0, 0),
        push_sent_count=3,
    )
    quota_storage.save_usage(usage)
    loaded = quota_storage.load_usage("u001", "2024-01-01")
    assert loaded is not None
    assert loaded.user_id == "u001"
    assert loaded.date == "2024-01-01"
    assert loaded.call_self_count == 2
    assert loaded.call_contact_count == 1
    assert loaded.call_answered_count == 1
    assert loaded.call_last_timestamp == datetime(2024, 1, 1, 10, 0, 0)
    assert loaded.call_timestamps == [
        datetime(2024, 1, 1, 9, 0, 0),
        datetime(2024, 1, 1, 10, 0, 0),
    ]
    assert loaded.chat_sent_count == 5
    assert loaded.chat_user_replied is True
    assert loaded.chat_last_timestamp == datetime(2024, 1, 1, 11, 0, 0)
    assert loaded.push_sent_count == 3


def test_quota_load_all_for_date(quota_storage):
    quota_storage.save_usage(DailyQuotaUsage(user_id="u001", date="2024-01-01"))
    quota_storage.save_usage(DailyQuotaUsage(user_id="u002", date="2024-01-01"))
    quota_storage.save_usage(DailyQuotaUsage(user_id="u003", date="2024-01-02"))
    results = quota_storage.load_all_for_date("2024-01-01")
    assert len(results) == 2
    ids = {r.user_id for r in results}
    assert ids == {"u001", "u002"}


def test_quota_reset_for_new_day(quota_storage):
    usage = quota_storage.reset_for_new_day("u001", "2024-01-02")
    assert usage.user_id == "u001"
    assert usage.date == "2024-01-02"
    assert usage.call_self_count == 0
    assert usage.chat_sent_count == 0
    loaded = quota_storage.load_usage("u001", "2024-01-02")
    assert loaded is not None
    assert loaded.call_self_count == 0


def test_quota_date_change_detection(quota_storage):
    old_usage = DailyQuotaUsage(
        user_id="u001",
        date="2024-01-01",
        call_self_count=3,
        chat_sent_count=2,
    )
    quota_storage.save_usage(old_usage)

    loaded = quota_storage.load_usage("u001", "2024-01-01")
    assert loaded is not None
    assert loaded.date == "2024-01-01"
    assert loaded.call_self_count == 3

    # Simulate date change: load for new date should return None, triggering reset
    new_loaded = quota_storage.load_usage("u001", "2024-01-02")
    assert new_loaded is None

    fresh = quota_storage.reset_for_new_day("u001", "2024-01-02")
    assert fresh.date == "2024-01-02"
    assert fresh.call_self_count == 0
    assert fresh.chat_sent_count == 0
