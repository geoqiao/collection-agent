"""Main agent session that handles events via Harness -> Decide -> Execute flow."""

from __future__ import annotations

from datetime import UTC, datetime

from collect_agent.compliance.checker import ComplianceChecker
from collect_agent.core.constants import EventType
from collect_agent.core.context import Context, OutreachResult
from collect_agent.core.models import Event, Message, UserState
from collect_agent.decider import Decider, Decision
from collect_agent.harness import Harness
from collect_agent.intent.models import IntentCategory
from collect_agent.skills.base import SkillResult
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.registry import SkillRegistry
from collect_agent.storage.memory_store import MemoryStore
from collect_agent.storage.sqlite_store import SQLiteStore

# Fixed templates for locked states
_LOCKED_TEMPLATES: dict[str, str] = {
    "escalated": "非常抱歉给您带来了不好的体验。您的投诉我已记录并升级至专人处理，后续将由投诉专员与您联系。",
    "stopped": "已收到您的要求。我已立即停止所有联系，并将您加入免打扰名单。",
    "crisis": "我非常理解您现在的感受。无论遇到什么困难，都有人愿意帮助您。请拨打心理援助热线 400-161-9995。",
    "disputed": "您的争议我已记录。在争议调查期间，我们将暂停催收联系。调查完成后我们会第一时间通知您。",
}


class AgentSession:
    """Main agent session — Harness -> Decide -> Execute."""

    def __init__(
        self,
        user_id: str,
        user_state: UserState,
        skill_registry: SkillRegistry,
        skill_executor: SkillExecutor,
        decider: Decider,
        harness: Harness,
        compliance_checker: ComplianceChecker | None = None,
        storage: MemoryStore | SQLiteStore | None = None,
    ) -> None:
        self.user_id = user_id
        self.user_state = user_state
        self.skill_registry = skill_registry
        self.skill_executor = skill_executor
        self.decider = decider
        self.harness = harness
        self.compliance_checker = compliance_checker
        self.storage = storage
        self.last_outreach_at: datetime | None = None
        self.last_interaction_at: datetime | None = None

    # Backward compatibility alias
    @property
    def state(self) -> UserState:
        return self.user_state

    async def handle_event(self, event: Event) -> SkillResult | None:
        """Handle an incoming event and return a skill result."""
        # Special events: bypass normal flow
        if event.type == EventType.USER_PAYMENT_SUCCESS:
            return await self._handle_payment_success(event)

        # 1. Harness checks
        harness_result = self.harness.check(event, self.user_state)
        if harness_result.block:
            return SkillResult(
                status="blocked",
                response_text=harness_result.force_response or "",
                thinking=f"Harness blocked: {harness_result.reason}",
            )

        # 2. Build context
        context = self._build_context(event)

        # 3. Decide (intent + skill selection)
        if harness_result.force_intent:
            decision = self._build_forced_decision(
                harness_result.force_intent, harness_result.reason
            )
        else:
            decision = await self.decider.decide(context)

        # 4. Load skill
        skill = self.skill_registry.get(decision.selected_skill)
        if skill is None:
            skill = self._fallback_skill(decision.intent)

        # 5. Record user message
        if event.type == EventType.USER_REPLIED:
            msg = event.payload.get("message", "")
            if msg:
                self._record_message("chatbot", "inbound", msg)
                self.user_state.conversation.negotiation_round += 1

        # 6. Execute skill via ReAct
        result = await self.skill_executor.execute(skill, context, self.storage)

        # 7. Output audit
        if result.response_text and self.compliance_checker:
            clean, reason = self.compliance_checker.audit_content(result.response_text)
            if not clean:
                result.response_text = self._fallback_for_violation(reason)
                result.status = "error"
                result.thinking += f"\n[Audit blocked: {reason}]"

        # 8. Record agent response
        if result.response_text:
            self._record_message("chatbot", "outbound", result.response_text)

        # 9. Process result (state transition, save)
        self._process_result(result, decision)

        return result

    def _build_context(self, event: Event) -> Context:
        """Build multi-signal context from event and user state."""
        profile = self.user_state.profile
        conversation = self.user_state.conversation

        # Recent events
        recent_events: list[Event] = []
        if event.type != EventType.USER_REPLIED:
            recent_events.append(event)

        # Last outreach
        last_outreach = None
        if self.last_outreach_at:
            hours = (datetime.now(UTC) - self.last_outreach_at).total_seconds() / 3600
            last_outreach = OutreachResult(
                hours_since=hours,
            )

        # Facts injection
        facts = {
            "user_name": profile.name or "用户",
            "due_amount": str(profile.amount_due),
            "overdue_days": str(profile.overdue_days),
            "occupation": profile.occupation or "未知",
        }

        # Available skills
        available_skills = [
            {"name": s.name, "description": s.description}
            for s in self.skill_registry.list_skills()
        ]

        return Context(
            user_message=event.payload.get("message") if event.type == EventType.USER_REPLIED else None,
            profile=profile,
            session_state=self.user_state.session_state,
            negotiation_round=conversation.negotiation_round,
            intent_history=self.user_state.intent_history,
            recent_events=recent_events,
            last_outreach=last_outreach,
            messages=conversation.messages,
            facts=facts,
            available_skills=available_skills,
        )

    def _build_forced_decision(self, intent: IntentCategory, reason: str) -> Decision:
        """Build a decision when harness forces an intent."""
        skill_name = self._intent_to_skill(intent)
        return Decision(
            intent=intent,
            selected_skill=skill_name,
            confidence="high",
            escalation=intent in (IntentCategory.CRISIS, IntentCategory.COMPLAINT, IntentCategory.DISPUTE),
            emotion="negative",
            reasoning=f"Harness forced: {reason}",
        )

    def _intent_to_skill(self, intent: IntentCategory) -> str:
        """Map intent to skill name (for harness-forced or fallback)."""
        mapping = {
            IntentCategory.COOPERATION: "payment_guidance",
            IntentCategory.NEGOTIATION: "negotiation",
            IntentCategory.AVOIDANCE: "reengage",
            IntentCategory.DISPUTE: "dispute",
            IntentCategory.COMPLAINT: "complaint",
            IntentCategory.STOP: "stop",
            IntentCategory.CRISIS: "crisis",
        }
        return mapping.get(intent, "troubleshoot")

    def _fallback_skill(self, intent: IntentCategory) -> str:
        """Fallback skill when LLM-selected skill is not found."""
        return self._intent_to_skill(intent)

    def _record_message(self, channel: str, direction: str, content: str) -> None:
        """Record a message to conversation history."""
        self.user_state.conversation.add_message(
            Message(
                channel=channel,
                direction=direction,
                content=content,
            )
        )

    def _process_result(self, result: SkillResult, decision: Decision) -> None:
        """Process skill result: update state, track intent history, save state."""
        # Update intent history
        if decision.intent:
            self.user_state.intent_history.append(decision.intent.value)
            self.user_state.conversation.current_intent = decision.intent.value

        # State transition
        if result.new_session_state:
            self.user_state.session_state = result.new_session_state
        else:
            # Auto-transition based on intent for one-way doors
            intent_to_state = {
                "STOP": "stopped",
                "CRISIS": "crisis",
                "COMPLAINT": "escalated",
                "DISPUTE": "disputed",
            }
            if decision.intent and decision.intent.value in intent_to_state:
                self.user_state.session_state = intent_to_state[decision.intent.value]

        # Update timestamps
        self.last_interaction_at = datetime.now(UTC)
        if result.status == "success" and result.response_text:
            self.last_outreach_at = datetime.now(UTC)

        # Save state
        if self.storage and hasattr(self.storage, "save"):
            self.storage.save(self.user_state)

    async def _handle_payment_success(self, event: Event) -> SkillResult:
        """Handle USER_PAYMENT_SUCCESS event directly."""
        self.user_state.session_state = "resolved"

        amount = event.payload.get("amount", 0)
        thinking = f"Payment successful: ¥{amount}. Transitioned to RESOLVED."

        # Record the payment event
        self._record_message("chatbot", "inbound", f"[系统] 用户支付 ¥{amount}")

        response_text = (
            f"感谢您的还款！您的账单已结清。"
            f"如有其他问题，欢迎随时联系。"
        )

        self._record_message("chatbot", "outbound", response_text)

        if self.storage and hasattr(self.storage, "save"):
            self.storage.save(self.user_state)

        return SkillResult(
            status="success",
            response_text=response_text,
            new_session_state="resolved",
            thinking=thinking,
        )

    def _fallback_for_violation(self, reason: str) -> str:
        """Return safe fallback message when audit blocks content."""
        return (
            "您好，关于您的账单问题，建议您通过官方客服热线咨询详情。"
            "如有任何疑问，我们随时为您服务。"
        )
