"""Centralized configuration manager."""

from pathlib import Path

import yaml

from collect_agent.config.models import AgentConfig, ComplianceConfig, LLMConfig, QuotaConfig, StorageConfig


class ConfigManager:
    """Single source of truth for all configuration.

    Loads config from YAML file and provides typed access to all sections.
    Supports hot-reloading for runtime config updates.
    """

    _instance: "ConfigManager | None" = None

    def __new__(cls, config_path: str = "config.yaml"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str = "config.yaml"):
        if self._initialized:
            return
        self._config_path = config_path
        self._config = self._load()
        self._initialized = True

    def _load(self) -> AgentConfig:
        path = Path(self._config_path)
        if not path.exists():
            return AgentConfig()

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return AgentConfig.model_validate(data)

    def reload(self) -> None:
        """Reload configuration from disk at runtime."""
        self._config = self._load()

    @property
    def config(self) -> AgentConfig:
        return self._config

    @property
    def llm(self) -> LLMConfig:
        return self._config.llm

    @property
    def compliance(self) -> ComplianceConfig:
        return self._config.compliance

    @property
    def quota(self) -> QuotaConfig:
        return self._config.quota

    @property
    def storage(self) -> StorageConfig:
        return self._config.storage

    # Convenience accessors for frequently used values

    @property
    def valid_hours(self) -> tuple[int, int]:
        """Compliance valid hours window (start, end)."""
        return self._config.compliance.valid_hours

    @property
    def db_path(self) -> str:
        return self._config.storage.db_path

    @property
    def llm_provider(self) -> str:
        return self._config.llm.provider

    def to_dict(self) -> dict:
        """Export current configuration as a plain dict."""
        return self._config.model_dump()
