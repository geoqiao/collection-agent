"""Session manager — creates and manages AgentSession instances."""

from __future__ import annotations

import warnings

from collect_agent.agent.session import AgentSession
from collect_agent.core.models import UserProfile, UserState
from collect_agent.intent.recognizer import IntentRecognizer
from collect_agent.llm.base import LLMClient
from collect_agent.llm.clients import MockLLMClient
from collect_agent.prompts.engine import PromptEngine
from collect_agent.session.enhanced_state_machine import StateMachine
from collect_agent.session.session import CollectionSession
from collect_agent.skills.base import Skill
from collect_agent.skills.complaint_skill import ComplaintSkill
from collect_agent.skills.crisis_skill import CrisisSkill
from collect_agent.skills.dispute_skill import DisputeSkill
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.followup_skill import FollowUpSkill
from collect_agent.skills.negotiation_skill import NegotiationSkill
from collect_agent.skills.onboard_skill import OnboardSkill
from collect_agent.skills.payment_guidance_skill import PaymentGuidanceSkill
from collect_agent.skills.reengage_skill import ReEngageSkill
from collect_agent.skills.registry import SkillRegistry
from collect_agent.skills.stop_skill import StopSkill
from collect_agent.skills.troubleshoot_skill import TroubleshootSkill
from collect_agent.storage.memory_store import MemoryStore
from collect_agent.storage.sqlite_store import SQLiteStore
from collect_agent.tools.billing import CreatePaymentPlanTool, QueryBillTool
from collect_agent.tools.compliance import (
    EscalateToHumanTool,
    PauseCollectionTool,
    WelfareAlertTool,
)
from collect_agent.tools.messaging import SendMessageTool, SendPaymentLinkTool
from collect_agent.tools.promises import CheckPaymentStatusTool, RecordPromiseTool
from collect_agent.tools.registry import ToolRegistry
from collect_agent.tools.user import (
    AddToDncListTool,
    QueryUserHistoryTool,
    ScheduleReminderTool,
)

# Default skill instances with their recommended tools
_DEFAULT_SKILLS: list[Skill] = [
    OnboardSkill(tools=[QueryBillTool(), QueryUserHistoryTool(), SendMessageTool()]),
    PaymentGuidanceSkill(tools=[QueryBillTool(), SendPaymentLinkTool()]),
    NegotiationSkill(
        tools=[
            QueryBillTool(),
            CreatePaymentPlanTool(),
            RecordPromiseTool(),
            ScheduleReminderTool(),
        ]
    ),
    ReEngageSkill(
        tools=[QueryUserHistoryTool(), SendMessageTool(), ScheduleReminderTool()]
    ),
    DisputeSkill(tools=[PauseCollectionTool(), EscalateToHumanTool()]),
    ComplaintSkill(tools=[PauseCollectionTool(), EscalateToHumanTool()]),
    CrisisSkill(
        tools=[PauseCollectionTool(), WelfareAlertTool(), EscalateToHumanTool()]
    ),
    StopSkill(tools=[AddToDncListTool(), PauseCollectionTool()]),
    TroubleshootSkill(tools=[SendMessageTool()]),
    FollowUpSkill(tools=[CheckPaymentStatusTool(), QueryBillTool(), SendMessageTool()]),
]

_DEFAULT_TOOLS = [
    QueryBillTool(),
    CreatePaymentPlanTool(),
    SendMessageTool(),
    SendPaymentLinkTool(),
    RecordPromiseTool(),
    CheckPaymentStatusTool(),
    PauseCollectionTool(),
    EscalateToHumanTool(),
    WelfareAlertTool(),
    QueryUserHistoryTool(),
    AddToDncListTool(),
    ScheduleReminderTool(),
]


def _create_default_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    for skill in _DEFAULT_SKILLS:
        registry.register(skill)
    return registry


def _create_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in _DEFAULT_TOOLS:
        registry.register(tool)
    return registry


class SessionManager:
    """Manages agent sessions per user.

    Creates AgentSession instances backed by the Skill-Based Agent architecture.
    """

    def __init__(
        self,
        store: MemoryStore | SQLiteStore | None = None,
        quota_manager=None,
        compliance_checker=None,
        llm_client: LLMClient | None = None,
        skill_registry: SkillRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
        prompt_engine: PromptEngine | None = None,
    ):
        self._store = store or SQLiteStore()
        self._quota_manager = quota_manager
        self._compliance_checker = compliance_checker
        self._llm_client = llm_client or MockLLMClient()
        self._skill_registry = skill_registry or _create_default_skill_registry()
        self._tool_registry = tool_registry or _create_default_tool_registry()
        self._prompt_engine = prompt_engine or PromptEngine()

        self._sessions: dict[str, AgentSession] = {}

    def get_or_create(self, user_id: str) -> AgentSession:
        if user_id in self._sessions:
            return self._sessions[user_id]

        state = self._store.load(user_id)
        if state is None:
            state = UserState(
                user_id=user_id,
                profile=UserProfile(user_id=user_id),
            )
            self._store.save(state)

        intent_recognizer = IntentRecognizer(self._llm_client)
        skill_executor = SkillExecutor(
            llm_client=self._llm_client,
            tool_registry=self._tool_registry,
            prompt_engine=self._prompt_engine,
        )

        session = AgentSession(
            user_id=user_id,
            user_state=state,
            skill_registry=self._skill_registry,
            intent_recognizer=intent_recognizer,
            state_machine=StateMachine(),
            skill_executor=skill_executor,
            tool_registry=self._tool_registry,
            prompt_engine=self._prompt_engine,
            llm_client=self._llm_client,
            storage=self._store,
            compliance_checker=self._compliance_checker,
        )
        self._sessions[user_id] = session
        return session

    def get(self, user_id: str) -> AgentSession | None:
        return self._sessions.get(user_id)

    def remove(self, user_id: str) -> None:
        if user_id in self._sessions:
            session = self._sessions[user_id]
            self._store.save(session.user_state)
            del self._sessions[user_id]

    # ─── Legacy compatibility ───

    def get_or_create_legacy(self, user_id: str) -> CollectionSession:
        """Create a legacy CollectionSession (deprecated, for migration only)."""
        warnings.warn(
            "CollectionSession is deprecated. Use AgentSession via get_or_create().",
            DeprecationWarning,
            stacklevel=2,
        )
        state = self._store.load(user_id)
        if state is None:
            state = UserState(
                user_id=user_id,
                profile=UserProfile(user_id=user_id),
            )
            self._store.save(state)

        return CollectionSession(
            user_id=user_id,
            state=state,
            quota_manager=self._quota_manager,
            compliance_checker=self._compliance_checker,
            llm_client=self._llm_client,
            storage=self._store,
        )
