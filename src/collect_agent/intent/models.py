"""Intent recognition models."""

from dataclasses import dataclass
from enum import Enum


class IntentCategory(Enum):
    COOPERATION = "A"  # 愿意还款
    NEGOTIATION = "B"  # 协商
    AVOIDANCE = "C"  # 回避/沉默
    DISPUTE = "D"  # 争议
    COMPLAINT = "E"  # 投诉/威胁
    STOP = "STOP"  # 要求停止联系
    CRISIS = "CRISIS"  # 危机信号
    UNREACHABLE = "F"  # 触达失败/联系不上
    INEFFECTIVE = "ineffective"
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
