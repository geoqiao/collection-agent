import pytest
from src.compliance.checker import ComplianceChecker
from src.core.models import UserProfile


@pytest.fixture
def checker():
    return ComplianceChecker()


def test_valid_hours_check(checker):
    from datetime import time
    assert checker.is_within_valid_hours(time(10, 0)) is True
    assert checker.is_within_valid_hours(time(7, 0)) is False
    assert checker.is_within_valid_hours(time(21, 0)) is False


def test_sensitive_occupation(checker):
    user = UserProfile(user_id="u001", occupation="律师")
    assert checker.is_sensitive(user) is True


def test_non_sensitive_occupation(checker):
    user = UserProfile(user_id="u002", occupation="工程师")
    assert checker.is_sensitive(user) is False


def test_complaint_keywords(checker):
    assert checker.is_complaint("我要投诉你们") is True
    assert checker.is_complaint("我会尽快还款") is False


def test_standard_template_for_sensitive(checker):
    user = UserProfile(user_id="u001", name="张三", occupation="律师", overdue_days=5, amount_due=1000.0)
    msg = checker.get_standard_message(user)
    assert "5" in msg
    assert "1000" in msg