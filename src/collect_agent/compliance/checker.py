from datetime import time

from collect_agent.compliance.rules import ComplianceRules
from collect_agent.core.models import UserProfile


class ComplianceChecker:
    def __init__(self, rules: ComplianceRules | None = None):
        self.rules = rules or ComplianceRules()

    def is_within_valid_hours(self, t: time | None = None) -> bool:
        if t is None:
            from datetime import datetime

            t = datetime.now().time()
        start = time(self.rules.valid_hours[0], 0)
        end = time(self.rules.valid_hours[1], 0)
        return start <= t < end

    def is_sensitive(self, user: UserProfile) -> bool:
        return user.is_sensitive

    def has_forbidden_words(self, content: str) -> bool:
        return any(word in content for word in self.rules.forbidden_words)

    def is_complaint(self, content: str) -> bool:
        return any(
            keyword in content for keyword in self.rules.complaint_keywords
        )

    def get_standard_message(self, user: UserProfile) -> str:
        return (
            f"您好，这里是 {{机构名称}}。您在 {{平台名称}} 的借款已逾期 {user.overdue_days} 天，"
            f"逾期金额 {user.amount_due} 元。逾期将影响您的个人信用记录，并可能产生罚息。"
            f"请您尽快安排还款。如有疑问，请联系客服 {{客服电话}}。"
        )

    def audit_content(self, content: str) -> tuple[bool, str]:
        """Layer 2 content audit. Returns (is_clean, reason)."""
        if self.has_forbidden_words(content):
            return False, "Content contains forbidden words"
        return True, ""
