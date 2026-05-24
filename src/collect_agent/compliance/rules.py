from pydantic import BaseModel, Field


class ComplianceRules(BaseModel):
    valid_hours: tuple[int, int] = (8, 20)
    max_call_per_hour: int = 3
    min_call_interval_minutes: int = 10
    forbidden_words: list[str] = Field(default_factory=lambda: [
        "法律诉讼", "法院起诉", "等着瞧", "后果自负", "后果严重",
        "弄死你", "杀了你", "威胁", "恐吓",
    ])
    complaint_keywords: list[str] = [
        "投诉", "举报", "律师", "法院", "银保监会",
        "报警", "媒体", "记者", "曝光",
    ]
    sensitive_occupations: list[str] = [
        "律师", "法官", "检察官", "警察",
        "政府官员", "公务员", "军人", "军人配偶",
        "记者", "媒体从业者",
    ]

    @classmethod
    def from_dict(cls, data: dict) -> "ComplianceRules":
        filtered = {k: v for k, v in data.items() if k in cls.model_fields}
        if "valid_hours" in data:
            filtered["valid_hours"] = tuple(data["valid_hours"])
        return cls(**filtered)