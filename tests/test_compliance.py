import pytest

from collect_agent.compliance.checker import ComplianceChecker
from collect_agent.core.models import UserProfile


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
    user = UserProfile(
        user_id="u001",
        name="张三",
        occupation="律师",
        overdue_days=5,
        amount_due=1000.0,
    )
    msg = checker.get_standard_message(user)
    assert "5" in msg
    assert "1000" in msg


def test_audit_content_clean(checker):
    is_clean, reason = checker.audit_content("您好，请尽快还款。")
    assert is_clean is True
    assert reason == ""


def test_audit_content_blocks_forbidden_words(checker):
    is_clean, reason = checker.audit_content("如果不还款，我们将采取法律诉讼。")
    assert is_clean is False
    assert "forbidden words" in reason


def test_audit_content_blocks_threats(checker):
    is_clean, reason = checker.audit_content("后果自负，等着瞧。")
    assert is_clean is False
    assert "forbidden words" in reason


def test_compliance_rules_has_forbidden_words():
    from collect_agent.compliance.rules import ComplianceRules

    rules = ComplianceRules()
    assert len(rules.forbidden_words) > 0
    assert "法律诉讼" in rules.forbidden_words
    assert "法院起诉" in rules.forbidden_words
