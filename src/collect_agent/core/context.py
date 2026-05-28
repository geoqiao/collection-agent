"""Multi-signal context for LLM decision-making."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from collect_agent.core.models import Event, Message, UserProfile


@dataclass
class OutreachResult:
    """Result of the last outbound outreach attempt."""

    message: str = ""
    response: str | None = None
    hours_since: float = 0.0


@dataclass
class Context:
    """Aggregates all signals for LLM consumption.

    Intent recognition is not just text classification — it is
    contextual inference from multiple signals.
    """

    # User text (if any)
    user_message: str | None = None

    # Static profile
    profile: UserProfile = field(default_factory=lambda: UserProfile(user_id=""))

    # Dynamic session state
    session_state: str = "normal"
    negotiation_round: int = 0
    intent_history: list[str] = field(default_factory=list)

    # Behavioural events (payment, login, etc.)
    recent_events: list[Event] = field(default_factory=list)

    # Last outreach result
    last_outreach: OutreachResult | None = None

    # Conversation history
    messages: list[Message] = field(default_factory=list)

    # Injected facts (bill amount, overdue days, etc.)
    facts: dict[str, Any] = field(default_factory=dict)

    # Available skills for LLM to choose from
    available_skills: list[dict[str, str]] = field(default_factory=list)

    def to_prompt(self) -> str:
        """Format all signals into a single prompt string.

        Uses XML tags for structured data — Chinese LLMs handle
        explicit tags more reliably than plain text descriptions.
        """
        parts: list[str] = []

        # Profile signal
        parts.append(
            f"【用户画像】逾期{self.profile.overdue_days}天，"
            f"金额¥{self.profile.amount_due}，"
            f"职业{self.profile.occupation or '未知'}，"
            f"敏感职业：{'是' if self.profile.is_sensitive else '否'}"
        )

        # Session state
        parts.append(
            f"【会话状态】{self.session_state}，协商轮数{self.negotiation_round}"
        )

        # Intent history
        if self.intent_history:
            parts.append(f"【意图历史】{', '.join(self.intent_history[-5:])}")

        # Behavioural events
        if self.recent_events:
            parts.append("【近期行为】")
            for ev in self.recent_events[-3:]:
                payload = ev.payload if ev.payload else {}
                parts.append(f"  - {ev.type.value}: {payload}")

        # Last outreach
        if self.last_outreach:
            msg = self.last_outreach.message[:80]
            resp = self.last_outreach.response or "无回复"
            parts.append(f"【上轮触达】{msg}...，用户反应：{resp}")

        # Conversation history
        if self.messages:
            parts.append("【最近对话】")
            for msg in self.messages[-5:]:
                direction = "用户" if msg.direction == "inbound" else "催收方"
                content = msg.content[:60]
                parts.append(f"  [{direction}] {content}")

        # Current message
        if self.user_message:
            parts.append(f"【本轮消息】{self.user_message}")
        else:
            parts.append("【本轮】用户未回复（outbound 触达）")

        # Injected facts (XML)
        if self.facts:
            facts_xml = "\n".join(
                f"  <{k}>{v}</{k}>" for k, v in self.facts.items()
            )
            parts.append(f"<facts>\n{facts_xml}\n</facts>")

        # Available skills
        if self.available_skills:
            parts.append("【可选 Skills】")
            for sk in self.available_skills:
                parts.append(f"  - {sk['name']}: {sk['description']}")

        return "\n\n".join(parts)
