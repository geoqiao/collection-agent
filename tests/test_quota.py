import asyncio
from datetime import datetime

import pytest

from collect_agent.quota.manager import QuotaManager
from collect_agent.quota.profile import QuotaProfile
from collect_agent.quota.usage import DailyQuotaUsage


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


@pytest.mark.asyncio
async def test_manager_get_usage(manager):
    usage = await manager.get_usage("u001")
    assert usage.user_id == "u001"
    assert usage.call_self_count == 0


@pytest.mark.asyncio
async def test_manager_record_call(manager):
    await manager.record_call_self("u001")
    usage = await manager.get_usage("u001")
    assert usage.call_self_count == 1


def test_rate_limit_interval():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    usage.call_last_timestamp = datetime.now()
    assert usage.can_call_with_interval(min_seconds=600) is False


@pytest.mark.asyncio
async def test_concurrent_get_usage_no_duplicates():
    """Concurrent access to QuotaManager shouldn't create duplicate records."""
    manager = QuotaManager()

    async def access():
        usage = await manager.get_usage("u001")
        return id(usage)

    ids = await asyncio.gather(*[access() for _ in range(20)])
    # All should return the same object
    assert len(set(ids)) == 1
    assert len(manager._usages) == 1


@pytest.mark.asyncio
async def test_cleanup_old_usages():
    """cleanup_old_usages removes records from previous days."""
    manager = QuotaManager()
    # Manually inject an old record
    manager._usages["u001:2024-01-01"] = DailyQuotaUsage(
        user_id="u001", date="2024-01-01"
    )
    manager._usages["u001:2099-01-01"] = DailyQuotaUsage(
        user_id="u001", date="2099-01-01"
    )

    manager.cleanup_old_usages()
    # Only today's record should remain (if today is not 2099-01-01)
    assert "u001:2024-01-01" not in manager._usages
    assert "u001:2099-01-01" not in manager._usages
