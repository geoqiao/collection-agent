"""Configuration models using Pydantic for validation."""

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "mock"
    model: str = ""
    api_key: str = ""
    temperature: float = 0.3
    max_tokens: int = 1024
    base_url: str = ""
    timeout: float = 30.0


class ComplianceConfig(BaseModel):
    valid_hours: tuple[int, int] = (8, 20)
    max_call_per_hour: int = 3
    min_call_interval_minutes: int = 10
    forbidden_words: list[str] = Field(
        default_factory=lambda: [
            "法律诉讼",
            "法院起诉",
            "等着瞧",
            "后果自负",
            "后果严重",
            "弄死你",
            "杀了你",
            "威胁",
            "恐吓",
        ]
    )
    complaint_keywords: list[str] = Field(
        default_factory=lambda: [
            "投诉",
            "举报",
            "律师",
            "法院",
            "银保监会",
            "报警",
            "媒体",
            "记者",
            "曝光",
        ]
    )
    sensitive_occupations: list[str] = Field(
        default_factory=lambda: [
            "律师",
            "法官",
            "检察官",
            "警察",
            "政府官员",
            "公务员",
            "军人",
            "军人配偶",
            "记者",
            "媒体从业者",
        ]
    )


class QuotaConfig(BaseModel):
    call_self_daily_max: int = 10
    call_contact_daily_max: int = 10
    call_answer_daily_max: int = 3
    chat_unanswered_daily_max: int = 5
    chat_answered_daily_max: int = 100
    push_daily_max: int = 1
    valid_hours: tuple[int, int] = (8, 20)
    max_call_per_hour: int = 3
    min_call_interval_seconds: int = 600
    min_chat_interval_unanswered: int = 1800
    min_chat_interval_answered: int = 120


class StorageConfig(BaseModel):
    db_path: str = "collect_agent.db"


class AgentConfig(BaseModel):
    """Root configuration for the collection agent system."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    quota: QuotaConfig = Field(default_factory=QuotaConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
