"""Main agent session that handles events via skill dispatch."""

from __future__ import annotations

from datetime import datetime

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserState
from collect_agent.intent.models import IntentResult
from collect_agent.intent.recognizer import IntentRecognizer
from collect_agent.llm.base import LLMClient
from collect_agent.prompts.engine import PromptEngine
from collect_agent.session.enhanced_state_machine import (
    AgentSessionState,
    StateMachine,
)
from collect_agent.skills.base import SkillContext, SkillResult, SkillResultStatus
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.registry import SkillRegistry
from collect_agent.compliance.checker import ComplianceChecker
from collect_agent.storage.memory_store import MemoryStore
from collect_agent.tools.registry import ToolRegistry


_FIXED_TEMPLATES: dict[str, str] = {
    "escalated": "非常抱歉给您带来了不好的体验。您的投诉我已记录并升级至专人处理，后续将由投诉专员与您联系。",
    "stopped": "已收到您的要求。我已立即停止所有联系，并将您加入免打扰名单。",
    "crisis": "我非常理解您现在的感受。无论遇到什么困难，都有人愿意帮助您。请拨打心理援助热线 400-161-9995。",
    "disputed": "您的争议我已记录。在争议调查期间，我们将暂停催收联系。调查完成后我们会第一时间通知您。",
}


class AgentSession:
    """Main agent session that handles events via skill dispatch."""

    def __init__(
        self,
        user_id: str,
        user_state: UserState,
        skill_registry: SkillRegistry,
        intent_recognizer: IntentRecognizer,
        state_machine: StateMachine,
        skill_executor: SkillExecutor,
        tool_registry: ToolRegistry,
        prompt_engine: PromptEngine,
        llm_client: LLMClient,
        storage: MemoryStore,
        compliance_checker: ComplianceChecker | None = None,
    ) -> None:
        self.user_id = user_id
        self.user_state = user_state
        self.skill_registry = skill_registry
        self.intent_recognizer = intent_recognizer
        self.state_machine = state_machine
        self.skill_executor = skill_executor
        self.tool_registry = tool_registry
        self.prompt_engine = prompt_engine
        self.llm_client = llm_client
        self.storage = storage
        self.compliance_checker = compliance_checker or ComplianceChecker()
        self.last_outreach_at: datetime | None = None
        self.last_interaction_at: datetime | None = None

    # Backward compatibility alias
    @property
    def state(self) -> UserState:
        return self.user_state

    async def handle_event(self, event: Event) -> SkillResult | None:
        """Handle an incoming event and return a skill result."""
        # Compliance check for outbound/outreach events
        if event.type in {
            EventType.SCHEDULED_OUTREACH,
            EventType.REMINDER_DUE,
            EventType.SILENCE_TIMEOUT,
        }:
            if not self.compliance_checker.is_within_valid_hours():
                return SkillResult(
                    status=SkillResultStatus.ERROR,
                    response_text="",
                    thinking="Outreach blocked: outside valid hours",
                )

        if event.type in (EventType.USER_REPLIED, EventType.CALL_CONNECTED):
            return await self._handle_user_event(event)

        if event.type in (
            EventType.SCHEDULED_OUTREACH,
            EventType.REMINDER_DUE,
            EventType.USER_LOGIN,
        ):
            return await self._handle_outreach_event(event)

        if event.type == EventType.USER_PAYMENT_SUCCESS:
            return await self._handle_payment_success(event)

        if event.type == EventType.SILENCE_TIMEOUT:
            return await self._handle_silence_timeout(event)

        return None

    async def _handle_user_event(self, event: Event) -> SkillResult:
        """Handle USER_REPLIED or CALL_CONNECTED events."""
        user_message = event.payload.get("message", "")
        session_state = self.state_machine.current.value

        # a. Recognize intent (with guardrails if locked)
        if self.state_machine.is_locked:
            intent_result = await self.intent_recognizer.recognize_with_guardrails(
                user_message=user_message,
                session_state=session_state,
            )
        else:
            intent_result = await self.intent_recognizer.recognize(
                user_message=user_message,
                context={
                    "session_state": session_state,
                    "history": self.user_state.conversation.messages,
                },
            )

        # Sync intent to user state for backward compatibility
        self.user_state.conversation.current_intent = intent_result.category.value

        # b. Check one-way door - if locked, return fixed template
        if self.state_machine.is_locked:
            state_value = self.state_machine.current.value
            return SkillResult(
                status=SkillResultStatus.SUCCESS,
                response_text=_FIXED_TEMPLATES.get(state_value, "感谢您的留言，我们将尽快处理。"),
                new_session_state=state_value,
                escalation=state_value in ("escalated", "crisis", "disputed"),
                thinking=f"One-way door state locked: {state_value}",
            )

        # c. Select skill from registry based on intent.category.value
        skill = self.skill_registry.select_skill(
            intent=intent_result.category.value,
            event_type=event.type.value,
            user_profile=self.user_state.profile,
        )

        if skill is None:
            # Fallback: try to match by intent name
            skill = self.skill_registry.get(intent_result.category.value.lower())

        if skill is None:
            return SkillResult(
                status=SkillResultStatus.ERROR,
                response_text="感谢您的留言，我已记录，稍后会有专人与您联系。",
                thinking=f"No skill found for intent: {intent_result.category.value}",
            )

        # d. Build SkillContext
        skill_ctx = self._build_skill_context(event, intent_result)

        # e. Execute skill via skill_executor
        skill_result = await self.skill_executor.execute(skill, skill_ctx)

        # f. Process result (update state machine, save state)
        self._process_skill_result(skill_result)

        # g. Return result
        return skill_result

    async def _handle_outreach_event(self, event: Event) -> SkillResult:
        """Handle SCHEDULED_OUTREACH / REMINDER_DUE / USER_LOGIN events."""
        skill = self.skill_registry.select_skill(
            intent=event.type.value,
            event_type=event.type.value,
            user_profile=self.user_state.profile,
        )

        if skill is None:
            skill = self.skill_registry.get("onboard")

        if skill is None:
            return SkillResult(
                status=SkillResultStatus.ERROR,
                response_text="系统错误：未找到 outreach 技能。",
                thinking=f"No skill found for event: {event.type.value}",
            )

        skill_ctx = self._build_skill_context(event, None)
        skill_result = await self.skill_executor.execute(skill, skill_ctx)
        self._process_skill_result(skill_result)
        return skill_result

    async def _handle_payment_success(self, event: Event) -> SkillResult:
        """Handle USER_PAYMENT_SUCCESS event."""
        self.state_machine.transition(AgentSessionState.RESOLVED)
        self.user_state.session_state = "resolved"
        self.storage.save(self.user_state)

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="感谢您的还款！您的账单已结清。如有其他问题，欢迎随时联系。",
            new_session_state="resolved",
            thinking="Payment successful, transitioned to RESOLVED.",
        )

    async def _handle_silence_timeout(self, event: Event) -> SkillResult:
        """Handle SILENCE_TIMEOUT event."""
        skill = self.skill_registry.get("re_engagement") or self.skill_registry.get("reengage")

        if skill is None:
            return SkillResult(
                status=SkillResultStatus.SUCCESS,
                response_text="您好，我们注意到您有一段时间没有回复了。如有任何疑问，请随时联系我们。",
                thinking="No re-engagement skill found, using fallback message.",
            )

        skill_ctx = self._build_skill_context(event, None)
        skill_result = await self.skill_executor.execute(skill, skill_ctx)
        self._process_skill_result(skill_result)
        return skill_result

    def _build_skill_context(
        self,
        event: Event,
        intent_result: IntentResult | None,
    ) -> SkillContext:
        """Build a SkillContext from event and intent."""
        return SkillContext(
            user_id=self.user_id,
            user_profile=self.user_state.profile,
            conversation_history=self.user_state.conversation.messages,
            current_intent=intent_result.category.value if intent_result else event.type.value,
            user_message=event.payload.get("message", ""),
            session_state=self.state_machine.current.value,
            available_tools=self.tool_registry.list_tools(),
            bill_facts=event.payload.get("bill_facts", {}),
        )

    def _process_skill_result(self, skill_result: SkillResult) -> None:
        """Process skill result: update state machine and save state."""
        if skill_result.new_session_state:
            state_mapping = {
                "escalated": AgentSessionState.ESCALATED,
                "stopped": AgentSessionState.STOPPED,
                "crisis": AgentSessionState.CRISIS,
                "disputed": AgentSessionState.DISPUTED,
                "resolved": AgentSessionState.RESOLVED,
                "paused": AgentSessionState.PAUSED,
                "normal": AgentSessionState.NORMAL,
                "pending_escalate": AgentSessionState.PENDING_ESCALATE,
            }
            target_state = state_mapping.get(skill_result.new_session_state)
            if target_state:
                self.state_machine.transition(target_state)
                self.user_state.session_state = skill_result.new_session_state

        # Save state synchronously for data integrity
        if hasattr(self.storage, "save"):
            self.storage.save(self.user_state)
