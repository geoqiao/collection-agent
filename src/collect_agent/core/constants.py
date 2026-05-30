from enum import Enum


class EventType(Enum):
    SCHEDULED_OUTREACH = "scheduled_outreach"
    REMINDER_DUE = "reminder_due"
    SILENCE_TIMEOUT = "silence_timeout"
    USER_LOGIN = "user_login"
    USER_PAYMENT_ATTEMPT = "user_payment_attempt"
    USER_PAYMENT_SUCCESS = "user_payment_success"
    USER_PAYMENT_FAIL = "user_payment_fail"
    CALL_CONNECTED = "call_connected"
    CALL_DISCONNECTED = "call_disconnected"
    CALL_NO_ANSWER = "call_no_answer"
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    USER_REPLIED = "user_replied"
    COMPLAINT = "complaint"
    QUOTA_EXHAUSTED = "quota_exhausted"
    COMPLIANCE_VIOLATION = "compliance_violation"
    PAYMENT_FOLLOW_UP = "payment_follow_up"


class ChannelType(Enum):
    VOICE = "voice"
    CHATBOT = "chatbot"
    PUSH = "push"


class Intent(Enum):
    WILLING_TO_PAY = "willing_to_pay"
    UNWILLING_TO_PAY = "unwilling_to_pay"
    INEFFECTIVE_CONTACT = "ineffective_contact"
    COMPLAINT = "complaint"
    PAYMENT_METHOD_INQUIRY = "payment_method_inquiry"
    OPERATION_INQUIRY = "operation_inquiry"


class SessionState(Enum):
    IDLE = "idle"
    OUTREACH_START = "outreach_start"
    INTENT_DETECTED = "intent_detected"
    FOLLOW_UP = "follow_up"
    RESOLVED = "resolved"


class AgentSessionState(Enum):
    """Enhanced state machine with flowing states and one-way doors."""

    # Flowing states (can transition freely)
    NORMAL = "normal"
    PENDING_ESCALATE = "pending_escalate"

    # One-way doors (irreversible)
    ESCALATED = "escalated"
    STOPPED = "stopped"
    CRISIS = "crisis"
    DISPUTED = "disputed"

    # Terminal states
    RESOLVED = "resolved"
    PAUSED = "paused"


class IntentCategory(Enum):
    COOPERATION = "A"  # 愿意还款
    NEGOTIATION = "B"  # 协商
    AVOIDANCE = "C"  # 回避/沉默
    DISPUTE = "D"  # 争议
    COMPLAINT = "E"  # 投诉
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


ONE_WAY_DOOR_STATES = {
    AgentSessionState.ESCALATED,
    AgentSessionState.STOPPED,
    AgentSessionState.CRISIS,
    AgentSessionState.DISPUTED,
}

FLOWING_STATES = {
    AgentSessionState.NORMAL,
    AgentSessionState.PENDING_ESCALATE,
}


class ChannelState(Enum):
    IDLE = "idle"
    SCHEDULED = "scheduled"
    OUTGOING = "outgoing"
    INTERACTING = "interacting"
    WAITING_REPLY = "waiting_reply"
    PAUSED = "paused"
    CLOSED = "closed"
