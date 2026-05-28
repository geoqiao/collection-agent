"""Harness — hard-rule guardrails that execute before any LLM call.

Like OpenClaw's Gateway policy: code-enforced, not LLM-decided.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserState
from collect_agent.intent.models import IntentCategory

# STOP/CRISIS keywords — zero-latency interception
_STOP_KEYWORDS = ["停止", "退订", "不要再打", "取消催收", "别再联系"]
_CRISIS_KEYWORDS = ["自杀", "不想活了", "活不下去", "重病", "绝症"]


@dataclass
class HarnessResult:
    """Result of harness checks."""

    block: bool = False
    reason: str = ""
    force_intent: IntentCategory | None = None
    force_response: str = ""


class Harness:
    """Hard-rule guardrails.

    These rules are enforced in code, not left to the LLM.
    """

    def __init__(self, compliance_checker=None, quota_manager=None) -> None:
        self._compliance = compliance_checker
        self._quota = quota_manager

    def check(self, event: Event, state: UserState) -> HarnessResult:
        """Run all harness checks."""
        # 1. Resolved / stopped / paused
        if state.session_state == "resolved":
            return HarnessResult(
                block=True,
                reason="already_resolved",
                force_response="您的账单已结清，如有其他问题请联系客服。",
            )

        if state.session_state in ("stopped",):
            return HarnessResult(
                block=True,
                reason="user_stopped",
            )

        if state.paused_until and state.paused_until > datetime.now(UTC):
            return HarnessResult(
                block=True,
                reason="paused",
                force_response="您的催收已暂停，恢复后我们会再联系您。",
            )

        # 2. Valid hours (for outbound events)
        if event.type in {
            EventType.SCHEDULED_OUTREACH,
            EventType.REMINDER_DUE,
            EventType.SILENCE_TIMEOUT,
        }:
            if self._compliance and not self._compliance.is_within_valid_hours():
                return HarnessResult(
                    block=True,
                    reason="outside_valid_hours",
                )

        # 3. Quota (for outbound events)
        if event.type in {
            EventType.SCHEDULED_OUTREACH,
            EventType.REMINDER_DUE,
            EventType.SILENCE_TIMEOUT,
        }:
            if self._quota:
                # TODO: implement per-channel quota check
                pass

        # 4. STOP / CRISIS keyword fast-path (inbound only)
        if event.type == EventType.USER_REPLIED:
            msg = event.payload.get("message", "")
            lowered = msg.lower()

            for kw in _STOP_KEYWORDS:
                if kw in lowered:
                    return HarnessResult(
                        block=False,
                        force_intent=IntentCategory.STOP,
                        reason=f"stop_keyword: {kw}",
                    )

            for kw in _CRISIS_KEYWORDS:
                if kw in lowered:
                    return HarnessResult(
                        block=False,
                        force_intent=IntentCategory.CRISIS,
                        reason=f"crisis_keyword: {kw}",
                    )

        # 5. Sensitive occupation — force standard reminder skill
        if state.profile.is_sensitive:
            return HarnessResult(
                block=False,
                reason="sensitive_occupation",
            )

        return HarnessResult(block=False)
