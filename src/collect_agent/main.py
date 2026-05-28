from collect_agent.compliance.checker import ComplianceChecker
from collect_agent.compliance.rules import ComplianceRules
from collect_agent.config import ConfigManager
from collect_agent.events.router import EventRouter
from collect_agent.llm.clients import create_llm_client
from collect_agent.quota.manager import QuotaManager
from collect_agent.quota.profile import QuotaProfile
from collect_agent.scheduler import OutreachScheduler
from collect_agent.session.manager import SessionManager
from collect_agent.storage.memory_store import MemoryStore
from collect_agent.storage.sqlite_store import SQLiteStore


class CollectAgentSystem:
    def __init__(
        self, store=None, llm_client=None, compliance_checker=None, quota_manager=None
    ):
        self.store = store or MemoryStore()
        self.session_manager = SessionManager(
            store=self.store,
            quota_manager=quota_manager,
            compliance_checker=compliance_checker,
            llm_client=llm_client,
        )
        self.router = EventRouter(self.session_manager)
        self.scheduler = OutreachScheduler(self)
        self._llm_client = llm_client
        self._compliance_checker = compliance_checker
        self._quota_manager = quota_manager

    @classmethod
    def from_config(cls, config_path: str = "config.yaml"):
        config_mgr = ConfigManager(config_path)
        cfg = config_mgr.config

        # Storage
        store = SQLiteStore(db_path=cfg.storage.db_path)

        # LLM client
        llm_client = create_llm_client(cfg.llm.model_dump())

        # Compliance
        compliance_rules = ComplianceRules.from_dict(cfg.compliance.model_dump())
        compliance_checker = ComplianceChecker(rules=compliance_rules)

        # Quota
        quota_profile = QuotaProfile.from_dict(cfg.quota.model_dump())
        quota_manager = QuotaManager(profile=quota_profile)

        system = cls(
            store=store,
            llm_client=llm_client,
            compliance_checker=compliance_checker,
            quota_manager=quota_manager,
        )
        return system

    def handle_event(self, event) -> None:
        self.router.route(event)

    def get_session(self, user_id: str):
        return self.session_manager.get(user_id)

    async def run_scheduled_outreach(self):
        await self.scheduler.scan_and_outreach()

    async def run_timeout_checks(self):
        await self.scheduler.check_silence_timeouts()
