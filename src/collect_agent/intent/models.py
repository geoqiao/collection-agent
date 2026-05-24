"""Intent recognition models."""

from dataclasses import dataclass
from enum import Enum


class IntentCategory(Enum):
    COOPERATION = "A"  # 合作
    NEGOTIATION = "B"  # 协商
    AVOIDANCE = "C"    # 回避
    DISPUTE = "D"      # 争议
    COMPLAINT = "E"    # 投诉/威胁
    STOP = "STOP"
    CRISIS = "CRISIS"
    INEFFECTIVE = "ineffective"  # 无效联系
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EmotionLevel(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANGRY = "angry"


@dataclass
class IntentResult:
    category: IntentCategory
    confidence: ConfidenceLevel
    escalation: bool
    emotion: EmotionLevel
    reasoning: str = ""
    raw_text: str = ""
