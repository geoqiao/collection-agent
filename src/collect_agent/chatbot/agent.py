"""Chatbot agent for multi-turn conversation in the chatbot channel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from collect_agent.core.models import Message, UserProfile
from collect_agent.intent.models import IntentCategory, IntentResult
from collect_agent.intent.recognizer import IntentRecognizer
from collect_agent.llm.base import LLMClient
from collect_agent.prompts.engine import PromptEngine
from collect_agent.session.enhanced_state_machine import ONE_WAY_DOOR_STATES, AgentSessionState, StateMachine
from collect_agent.skills.base import SkillContext, SkillResult, SkillResultStatus
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.registry import SkillRegistry
from collect_agent.tools.base import Tool


@dataclass
class ChatContext:
    """Context for a chatbot conversation turn."""

    user_id: str
    user_profile: UserProfile
    conversation_history: list[Message] = field(default_factory=list)
    bill_facts: dict[str, Any] = field(default_factory=dict)
    session_state: str = "normal"
    available_tools: list[Tool] = field(default_factory=list)


@dataclass
class ChatbotResponse:
    """Response from the chatbot agent."""

    message: str
    intent: str = ""
    confidence: str = ""
    escalation: bool = False
    thinking: str = ""
    new_session_state: str | None = None


_ONE_WAY_DOOR_INTENTS = {
    IntentCategory.STOP,
    IntentCategory.CRISIS,
    IntentCategory.COMPLAINT,
    IntentCategory.DISPUTE,
}


class ChatbotAgent:
    """Independent conversation agent for chatbot channel.

    Manages multi-turn dialogue, tool calling via SkillExecutor, and context.
    """

    FIXED_TEMPLATES: dict[str, str] = {
        "escalated": "非常抱歉给您带来了不好的体验。您的投诉我已记录并升级至专人处理，后续将由投诉专员与您联系。",
        "stopped": "已收到您的要求。我已立即停止所有联系，并将您加入免打扰名单。",
        "crisis": "我非常理解您现在的感受。无论遇到什么困难，都有人愿意帮助您。请拨打心理援助热线 400-161-9995。",
        "disputed": "您的争议我已记录。在争议调查期间，我们将暂停催收联系。调查完成后我们会第一时间通知您。",
    }

    def __init__(
        self,
        llm_client: LLMClient,
        skill_executor: SkillExecutor,
        intent_recognizer: IntentRecognizer,
        prompt_engine: PromptEngine,
        skill_registry: SkillRegistry | None = None,
        max_turns: int = 10,
    ) -> None:
        self.llm_client = llm_client
        self.skill_executor = skill_executor
        self.intent_recognizer = intent_recognizer
        self.prompt_engine = prompt_engine
        self.skill_registry = skill_registry
        self.max_turns = max_turns

    async def handle_message(
        self,
        user_id: str,
        user_message: str,
        context: ChatContext,
    ) -> ChatbotResponse:
        """Handle a single user message in the chatbot channel."""
        # 1. Check if session is locked in a one-way door state
        if context.session_state in self.FIXED_TEMPLATES:
            return ChatbotResponse(
                message=self.FIXED_TEMPLATES[context.session_state],
                intent=context.session_state,
                confidence="high",
                escalation=context.session_state in ("escalated", "crisis", "disputed"),
                thinking="One-way door state: returning fixed template.",
                new_session_state=context.session_state,
            )

        # 2. Run intent recognition
        intent_result = await self.intent_recognizer.recognize(
            user_message=user_message,
            context={
                "session_state": context.session_state,
                "history": context.conversation_history,
            },
        )

        # 3. Check one-way door intents
        if intent_result.category in _ONE_WAY_DOOR_INTENTS:
            template_key = self._intent_to_template_key(intent_result.category)
            new_state = self._intent_to_state(intent_result.category)
            return ChatbotResponse(
                message=self.FIXED_TEMPLATES.get(template_key, "感谢您的留言，我们将尽快处理。"),
                intent=intent_result.category.value,
                confidence=intent_result.confidence.value,
                escalation=intent_result.escalation,
                thinking=intent_result.reasoning,
                new_session_state=new_state,
            )

        # 4. Build SkillContext and execute skill via skill_executor
        skill_ctx = SkillContext(
            user_id=user_id,
            user_profile=context.user_profile,
            conversation_history=context.conversation_history,
            current_intent=intent_result.category.value,
            user_message=user_message,
            session_state=context.session_state,
            available_tools=context.available_tools,
            bill_facts=context.bill_facts,
        )

        # Determine which skill to execute based on intent
        skill = self._resolve_skill(intent_result)
        if skill is None:
            return ChatbotResponse(
                message="感谢您的留言，我已记录，稍后会有专人与您联系。",
                intent=intent_result.category.value,
                confidence=intent_result.confidence.value,
                escalation=intent_result.escalation,
                thinking=intent_result.reasoning,
                new_session_state=context.session_state,
            )

        skill_result = await self.skill_executor.execute(skill, skill_ctx)

        # 5. Return ChatbotResponse
        return ChatbotResponse(
            message=skill_result.response_text or "",
            intent=intent_result.category.value,
            confidence=intent_result.confidence.value,
            escalation=skill_result.escalation or intent_result.escalation,
            thinking=skill_result.thinking or intent_result.reasoning,
            new_session_state=skill_result.new_session_state or context.session_state,
        )

    def _intent_to_template_key(self, category: IntentCategory) -> str:
        mapping = {
            IntentCategory.STOP: "stopped",
            IntentCategory.CRISIS: "crisis",
            IntentCategory.COMPLAINT: "escalated",
            IntentCategory.DISPUTE: "disputed",
        }
        return mapping.get(category, "")

    def _intent_to_state(self, category: IntentCategory) -> str:
        mapping = {
            IntentCategory.STOP: "stopped",
            IntentCategory.CRISIS: "crisis",
            IntentCategory.COMPLAINT: "escalated",
            IntentCategory.DISPUTE: "disputed",
        }
        return mapping.get(category, "normal")

    def _resolve_skill(self, intent_result: IntentResult) -> Any:
        """Resolve a skill based on intent result."""
        if self.skill_registry is None:
            return None
        skill = self.skill_registry.select_skill(
            intent=intent_result.category.value,
            user_profile=None,
        )
        if skill is None:
            skill = self.skill_registry.get(intent_result.category.value.lower())
        return skill
