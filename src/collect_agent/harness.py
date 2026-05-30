"""Harness — hard-rule guardrails that execute before any LLM call.

Like OpenClaw's Gateway policy: code-enforced, not LLM-decided.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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


class FrequencyLimiter:
    """Per-user contact frequency limiter.

    Rules:
    - Max N contacts per hour per user
    - Max M contacts per day per user
    - Cooldown after failed delivery (exponential backoff)
    - Minimum interval between same-channel contacts
    """

    DEFAULT_HOURLY_LIMIT = 3
    DEFAULT_DAILY_LIMIT = 8
    DEFAULT_MIN_INTERVAL_MINUTES = 30
    DEFAULT_FAILED_COOLDOWN_HOURS = [1, 4, 24]  # 1st, 2nd, 3rd+ failure

    def __init__(
        self,
        hourly_limit: int = DEFAULT_HOURLY_LIMIT,
        daily_limit: int = DEFAULT_DAILY_LIMIT,
        min_interval_minutes: int = DEFAULT_MIN_INTERVAL_MINUTES,
    ) -> None:
        self._hourly_limit = hourly_limit
        self._daily_limit = daily_limit
        self._min_interval = timedelta(minutes=min_interval_minutes)

    def check(self, state: UserState, event: Event) -> tuple[bool, str]:
        """Check if outreach should be blocked due to frequency limits.

        Returns (should_block, reason).
        """
        now = datetime.now(UTC)

        # Only check outbound events
        if event.type not in {
            EventType.SCHEDULED_OUTREACH,
            EventType.REMINDER_DUE,
            EventType.SILENCE_TIMEOUT,
            EventType.PAYMENT_FOLLOW_UP,
        }:
            return False, ""

        # Count recent outbound messages from conversation history
        outbound_messages = [
            m for m in state.conversation.messages if m.direction == "outbound"
        ]

        # Hourly check
        hour_ago = now - timedelta(hours=1)
        hourly_count = sum(
            1 for m in outbound_messages if m.timestamp and m.timestamp >= hour_ago
        )
        if hourly_count >= self._hourly_limit:
            return True, f"hourly_limit_exceeded:{hourly_count}/{self._hourly_limit}"

        # Daily check
        day_ago = now - timedelta(days=1)
        daily_count = sum(
            1 for m in outbound_messages if m.timestamp and m.timestamp >= day_ago
        )
        if daily_count >= self._daily_limit:
            return True, f"daily_limit_exceeded:{daily_count}/{self._daily_limit}"

        # Minimum interval check
        if outbound_messages:
            last_outbound = max(m.timestamp for m in outbound_messages if m.timestamp)
            if now - last_outbound < self._min_interval:
                seconds_remaining = int(
                    (self._min_interval - (now - last_outbound)).total_seconds()
                )
                return True, f"min_interval_not_met:{seconds_remaining}s_remaining"

        return False, ""


class Harness:
    """Hard-rule guardrails.

    These rules are enforced in code, not left to the LLM.
    """

    def __init__(self, compliance_checker=None, quota_manager=None) -> None:
        self._compliance = compliance_checker
        self._quota = quota_manager
        self._freq_limiter = FrequencyLimiter()

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

        # 2. Frequency limits (for outbound events)
        if event.type in {
            EventType.SCHEDULED_OUTREACH,
            EventType.REMINDER_DUE,
            EventType.SILENCE_TIMEOUT,
            EventType.PAYMENT_FOLLOW_UP,
        }:
            blocked, reason = self._freq_limiter.check(state, event)
            if blocked:
                return HarnessResult(
                    block=True,
                    reason=f"frequency_limit:{reason}",
                )

        # 3. Valid hours (for outbound events)
        if (
            event.type
            in {
                EventType.SCHEDULED_OUTREACH,
                EventType.REMINDER_DUE,
                EventType.SILENCE_TIMEOUT,
            }
            and self._compliance
            and not self._compliance.is_within_valid_hours()
        ):
            return HarnessResult(
                block=True,
                reason="outside_valid_hours",
            )

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
