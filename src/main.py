import yaml

from src.compliance.checker import ComplianceChecker
from src.events.router import EventRouter
from src.llm.clients import create_llm_client
from src.quota.manager import QuotaManager
from src.scheduler import OutreachScheduler
from src.session.manager import SessionManager
from src.storage.memory_store import MemoryStore
from src.storage.sqlite_store import SQLiteStore


class CollectAgentSystem:
    def __init__(self, store=None, llm_client=None, compliance_checker=None, quota_manager=None):
        self.store = store or MemoryStore()
        self.session_manager = SessionManager(self.store)
        self.router = EventRouter(self.session_manager)
        self.scheduler = OutreachScheduler(self)
        self._llm_client = llm_client
        self._compliance_checker = compliance_checker
        self._quota_manager = quota_manager

    @classmethod
    def from_config(cls, config_path: str = "config.yaml"):
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        llm_config = config.get("llm", {})
        compliance_config = config.get("compliance", {})
        quota_config = config.get("quota", {})
        storage_config = config.get("storage", {})

        # Storage
        db_path = storage_config.get("db_path", "collect_agent.db")
        store = SQLiteStore(db_path=db_path)

        # LLM client
        llm_client = create_llm_client(llm_config)

        # Compliance
        compliance_checker = ComplianceChecker()
        if "valid_hours" in compliance_config:
            compliance_checker.rules.valid_hours = tuple(compliance_config["valid_hours"])
        if "max_call_per_hour" in compliance_config:
            compliance_checker.rules.max_call_per_hour = compliance_config["max_call_per_hour"]
        if "min_call_interval_minutes" in compliance_config:
            compliance_checker.rules.min_call_interval_minutes = compliance_config["min_call_interval_minutes"]

        # Quota
        quota_manager = QuotaManager()
        if "call_self_daily_max" in quota_config:
            quota_manager._profile.call_self_daily_max = quota_config["call_self_daily_max"]
        if "call_contact_daily_max" in quota_config:
            quota_manager._profile.call_contact_daily_max = quota_config["call_contact_daily_max"]
        if "call_answer_daily_max" in quota_config:
            quota_manager._profile.call_answer_daily_max = quota_config["call_answer_daily_max"]
        if "chat_unanswered_daily_max" in quota_config:
            quota_manager._profile.chat_unanswered_daily_max = quota_config["chat_unanswered_daily_max"]
        if "chat_answered_daily_max" in quota_config:
            quota_manager._profile.chat_answered_daily_max = quota_config["chat_answered_daily_max"]
        if "push_daily_max" in quota_config:
            quota_manager._profile.push_daily_max = quota_config["push_daily_max"]

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
