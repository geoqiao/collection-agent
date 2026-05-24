"""Tests for the configuration layer."""

import tempfile
from pathlib import Path

from collect_agent.config import ConfigManager
from collect_agent.config.models import AgentConfig, ComplianceConfig, LLMConfig, QuotaConfig, StorageConfig


class TestConfigModels:
    def test_default_agent_config(self):
        cfg = AgentConfig()
        assert cfg.llm.provider == "mock"
        assert cfg.compliance.valid_hours == (8, 20)
        assert cfg.quota.call_self_daily_max == 10
        assert cfg.storage.db_path == "collect_agent.db"

    def test_compliance_config_defaults(self):
        cfg = ComplianceConfig()
        assert cfg.valid_hours == (8, 20)
        assert cfg.max_call_per_hour == 3
        assert cfg.min_call_interval_minutes == 10
        assert "法律诉讼" in cfg.forbidden_words
        assert "投诉" in cfg.complaint_keywords
        assert "律师" in cfg.sensitive_occupations

    def test_llm_config_defaults(self):
        cfg = LLMConfig()
        assert cfg.provider == "mock"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 1024
        assert cfg.timeout == 30.0

    def test_quota_config_defaults(self):
        cfg = QuotaConfig()
        assert cfg.call_self_daily_max == 10
        assert cfg.push_daily_max == 1
        assert cfg.valid_hours == (8, 20)
        assert cfg.min_call_interval_seconds == 600

    def test_storage_config_defaults(self):
        cfg = StorageConfig()
        assert cfg.db_path == "collect_agent.db"

    def test_custom_valid_hours(self):
        cfg = ComplianceConfig(valid_hours=(9, 18))
        assert cfg.valid_hours == (9, 18)

    def test_model_validation(self):
        data = {
            "compliance": {"valid_hours": [9, 21], "max_call_per_hour": 5},
            "llm": {"provider": "openai", "temperature": 0.5},
            "quota": {"call_self_daily_max": 20},
            "storage": {"db_path": "test.db"},
        }
        cfg = AgentConfig.model_validate(data)
        assert cfg.compliance.valid_hours == (9, 21)
        assert cfg.compliance.max_call_per_hour == 5
        assert cfg.llm.provider == "openai"
        assert cfg.quota.call_self_daily_max == 20
        assert cfg.storage.db_path == "test.db"


class TestConfigManager:
    def test_singleton(self):
        # Reset singleton for test
        ConfigManager._instance = None

        cm1 = ConfigManager("dummy.yaml")
        cm2 = ConfigManager("other.yaml")
        assert cm1 is cm2

    def test_loads_defaults_when_file_missing(self):
        ConfigManager._instance = None
        cm = ConfigManager("/nonexistent/config.yaml")
        assert cm.config.compliance.valid_hours == (8, 20)
        assert cm.llm.provider == "mock"

    def test_loads_from_yaml_file(self):
        ConfigManager._instance = None
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
compliance:
  valid_hours: [9, 18]
  max_call_per_hour: 5
llm:
  provider: openai
  temperature: 0.7
quota:
  call_self_daily_max: 15
storage:
  db_path: custom.db
""")
            path = f.name

        try:
            cm = ConfigManager(path)
            assert cm.config.compliance.valid_hours == (9, 18)
            assert cm.config.compliance.max_call_per_hour == 5
            assert cm.llm.provider == "openai"
            assert cm.llm.temperature == 0.7
            assert cm.quota.call_self_daily_max == 15
            assert cm.storage.db_path == "custom.db"
        finally:
            Path(path).unlink()

    def test_reload_updates_config(self):
        ConfigManager._instance = None
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("compliance:\n  valid_hours: [9, 18]\n")
            path = f.name

        try:
            cm = ConfigManager(path)
            assert cm.valid_hours == (9, 18)

            # Update file
            with open(path, "w") as f:
                f.write("compliance:\n  valid_hours: [10, 22]\n")

            cm.reload()
            assert cm.valid_hours == (10, 22)
        finally:
            Path(path).unlink()

    def test_convenience_accessors(self):
        ConfigManager._instance = None
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("compliance:\n  valid_hours: [7, 21]\nstorage:\n  db_path: test.db\nllm:\n  provider: claude\n")
            path = f.name

        try:
            cm = ConfigManager(path)
            assert cm.valid_hours == (7, 21)
            assert cm.db_path == "test.db"
            assert cm.llm_provider == "claude"
        finally:
            Path(path).unlink()

    def test_to_dict(self):
        ConfigManager._instance = None
        cm = ConfigManager("/nonexistent.yaml")
        d = cm.to_dict()
        assert d["compliance"]["valid_hours"] == (8, 20)
        assert d["llm"]["provider"] == "mock"
