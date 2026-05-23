from pydantic import BaseModel, Field


class ComplianceRules(BaseModel):
    valid_hours: tuple[int, int] = (8, 20)
    max_call_per_hour: int = 3
    min_call_interval_minutes: int = 10
    forbidden_words: list[str] = Field(default_factory=list)
    complaint_keywords: list[str] = [
        "投诉", "举报", "律师", "法院", "银保监会",
        "报警", "媒体", "记者", "曝光",
    ]
    sensitive_occupations: list[str] = [
        "律师", "法官", "检察官", "警察",
        "政府官员", "公务员", "军人", "军人配偶",
        "记者", "媒体从业者",
    ]