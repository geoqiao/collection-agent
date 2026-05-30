"""Session manager — creates and manages AgentSession instances.

Architecture: shared heavy-weight dependencies, lightweight per-user sessions.
AgentSession objects are created on-demand per event and are NOT cached
in memory (unless enable_cache=True). All state lives in storage.
"""

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
    """Manages agent sessions per user.

    Heavy-weight dependencies (LLM, skills, tools) are created once and shared.
    AgentSession objects are lightweight wrappers created per event.
    No in-memory session cache — state is always loaded from storage.
    """

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

        # Heavy-weight dependencies — created once, shared across all sessions
        self._skill_registry = skill_registry or self._load_default_skills()
        self._tool_registry = tool_registry or get_registry()
        self._harness = Harness(
            compliance_checker=self._compliance_checker,
            quota_manager=self._quota_manager,
        )
        self._decider = Decider(
            llm_client=self._llm_client,
            skill_registry=self._skill_registry,
        )
        self._skill_executor = SkillExecutor(
            llm_client=self._llm_client,
            tool_registry=self._tool_registry,
        )

    def _load_default_skills(self) -> SkillRegistry:
        """Load skills from Markdown files."""
        registry = SkillRegistry()
        loader = SkillLoader()
        for skill in loader.load_all():
            registry.register(skill)
        return registry

    def get_or_create(self, user_id: str) -> AgentSession:
        """Create a lightweight AgentSession for the user.

        State is loaded fresh from storage on every call.
        Heavy-weight dependencies are injected from shared instances.
        """
        state = self._store.load(user_id)
        if state is None:
            state = UserState(
                user_id=user_id,
                profile=UserProfile(user_id=user_id),
            )
            self._store.save(state)

        # Ensure transient fields are present on older states
        if state.intent_history is None:
            state.intent_history = []
        if state.silence_timeout_emitted is None:
            state.silence_timeout_emitted = []

        return AgentSession(
            user_id=user_id,
            user_state=state,
            skill_registry=self._skill_registry,
            skill_executor=self._skill_executor,
            decider=self._decider,
            harness=self._harness,
            compliance_checker=self._compliance_checker,
            storage=self._store,
        )

    def get(self, user_id: str) -> UserState | None:
        """Return raw user state from storage (for inspection)."""
        return self._store.load(user_id)

    def save(self, user_id: str) -> None:
        """Explicitly save user state to storage."""
        state = self._store.load(user_id)
        if state is not None:
            self._store.save(state)

    @property
    def store(self):
        return self._store
