import pytest
from datetime import datetime
from src.quota.profile import QuotaProfile
from src.quota.usage import DailyQuotaUsage
from src.quota.manager import QuotaManager


def test_quota_profile_defaults():
    qp = QuotaProfile()
    assert qp.call_self_daily_max == 10
    assert qp.chat_unanswered_daily_max == 5
    assert qp.push_daily_max == 1


def test_daily_usage_increment():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    usage.increment_call_self()
    assert usage.call_self_count == 1


def test_can_call_within_limit():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    profile = QuotaProfile()
    assert usage.can_call_self(profile) is True


def test_cannot_call_over_limit():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    profile = QuotaProfile()
    usage.call_self_count = 10
    assert usage.can_call_self(profile) is False


@pytest.fixture
def manager():
    return QuotaManager()


def test_manager_get_usage(manager):
    usage = manager.get_usage("u001")
    assert usage.user_id == "u001"
    assert usage.call_self_count == 0


def test_manager_record_call(manager):
    manager.record_call_self("u001")
    usage = manager.get_usage("u001")
    assert usage.call_self_count == 1


def test_rate_limit_interval():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    usage.call_last_timestamp = datetime.now()
    assert usage.can_call_with_interval(min_seconds=600) is False