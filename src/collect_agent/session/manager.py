"""Session manager — creates and manages AgentSession instances."""

from __future__ import annotations

from collect_agent.agent.session import AgentSession
from collect_agent.core.models import UserProfile, UserState
from collect_agent.decider import Decider
from collect_agent.harness import Harness
from collect_agent.llm.base import LLMClient
from collect_agent.llm.clients import MockLLMClient
from collect_agent.skills.executor import SkillExecutor
from collect_agent.skills.loader import SkillLoader
from collect_agent.skills.registry import SkillRegistry
from collect_agent.storage.memory_store import MemoryStore
from collect_agent.storage.sqlite_store import SQLiteStore
from collect_agent.tools.registry import ToolRegistry, get_registry


class SessionManager:
    """Manages agent sessions per user."""

    def __init__(
        self,
        store: MemoryStore | SQLiteStore | None = None,
        quota_manager=None,
        compliance_checker=None,
        llm_client: LLMClient | None = None,
        skill_registry: SkillRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        self._store = store or SQLiteStore()
        self._quota_manager = quota_manager
        self._compliance_checker = compliance_checker
        self._llm_client = llm_client or MockLLMClient()
        self._skill_registry = skill_registry or self._load_default_skills()
        self._tool_registry = tool_registry or get_registry()

        self._sessions: dict[str, AgentSession] = {}

    def _load_default_skills(self) -> SkillRegistry:
        """Load skills from Markdown files."""
        registry = SkillRegistry()
        loader = SkillLoader()
        for skill in loader.load_all():
            registry.register(skill)
        return registry

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

        harness = Harness(
            compliance_checker=self._compliance_checker,
            quota_manager=self._quota_manager,
        )
        decider = Decider(
            llm_client=self._llm_client,
            skill_registry=self._skill_registry,
        )
        skill_executor = SkillExecutor(
            llm_client=self._llm_client,
            tool_registry=self._tool_registry,
        )

        session = AgentSession(
            user_id=user_id,
            user_state=state,
            skill_registry=self._skill_registry,
            skill_executor=skill_executor,
            decider=decider,
            harness=harness,
            compliance_checker=self._compliance_checker,
            storage=self._store,
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
