"""E2E test cases for Collect Agent.

Each test case defines a user message + expected behavior checkpoints.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from collect_agent.intent.models import IntentCategory


@dataclass
class IntentCheck:
    """Expected intent classification."""

    category: IntentCategory
    min_confidence: str = "medium"  # low, medium, high
    allow_escalation: bool | None = None


@dataclass
class ResponseCheck:
    """Expected characteristics of the agent's response."""

    # Must NOT contain these substrings
    forbidden_substrings: list[str] = field(default_factory=list)
    # Should contain at least one of these
    required_substrings: list[str] = field(default_factory=list)
    # Max length
    max_length: int = 0
    # Should mention amount
    should_mention_amount: bool = False
    # Should mention overdue days
    should_mention_overdue: bool = False


@dataclass
class TestCase:
    name: str
    description: str
    user_message: str
    overdue_days: int = 5
    amount_due: float = 1000.0
    negotiation_round: int = 0
    session_state: str = "normal"
    occupation: str | None = None

    intent_check: IntentCheck | None = None
    response_check: ResponseCheck | None = None
    # Extra assertions: function(result) -> list[str] of error messages
    extra_assertions: Callable | None = None


# ─── Test Suite ───

INTENT_ACCURACY_TESTS = [
    TestCase(
        name="cooperation_explicit",
        description="用户明确表达还款意愿",
        user_message="我会还的，给我几天时间",
        intent_check=IntentCheck(
            category=IntentCategory.COOPERATION, min_confidence="medium"
        ),
        response_check=ResponseCheck(
            forbidden_substrings=["停止", "退订", "免打扰"],
        ),
    ),
    TestCase(
        name="cooperation_willing",
        description="用户说愿意处理",
        user_message="我愿意还款，请问怎么操作？",
        intent_check=IntentCheck(
            category=IntentCategory.COOPERATION, min_confidence="medium"
        ),
    ),
    TestCase(
        name="cooperation_fuzzy_pay",
        description="模糊承诺但非STOP关键词",
        user_message="我会还的",
        intent_check=IntentCheck(
            category=IntentCategory.COOPERATION, min_confidence="medium"
        ),
        response_check=ResponseCheck(
            forbidden_substrings=["停止", "退订", "免打扰"],
        ),
    ),
    TestCase(
        name="negotiation_difficulty",
        description="用户表示有困难",
        user_message="我现在手头紧，能不能延期？",
        intent_check=IntentCheck(
            category=IntentCategory.NEGOTIATION, min_confidence="medium"
        ),
    ),
    TestCase(
        name="negotiation_installment",
        description="用户询问分期",
        user_message="可以分期还吗？",
        intent_check=IntentCheck(
            category=IntentCategory.NEGOTIATION, min_confidence="medium"
        ),
    ),
    TestCase(
        name="avoidance_vague",
        description="用户回避问题",
        user_message="我知道了，再说吧",
        intent_check=IntentCheck(
            category=IntentCategory.AVOIDANCE, min_confidence="low"
        ),
    ),
    TestCase(
        name="dispute_amount",
        description="用户质疑金额",
        user_message="这个金额不对吧，我没借这么多",
        intent_check=IntentCheck(
            category=IntentCategory.DISPUTE, min_confidence="medium"
        ),
    ),
    TestCase(
        name="complaint_threat",
        description="用户威胁投诉",
        user_message="你们再骚扰我我就去银保监会投诉",
        intent_check=IntentCheck(
            category=IntentCategory.COMPLAINT,
            min_confidence="medium",
            allow_escalation=True,
        ),
    ),
    TestCase(
        name="stop_explicit",
        description="用户明确要求停止联系",
        user_message="不要再给我打电话了，退订",
        intent_check=IntentCheck(
            category=IntentCategory.STOP, min_confidence="high"
        ),
    ),
    TestCase(
        name="stop_keyword",
        description="用户说停止",
        user_message="停止催收，取消",
        intent_check=IntentCheck(
            category=IntentCategory.STOP, min_confidence="high"
        ),
    ),
    TestCase(
        name="crisis_signal",
        description="用户表达自杀倾向",
        user_message="我真的不想活了，你们逼死我算了",
        intent_check=IntentCheck(
            category=IntentCategory.CRISIS,
            min_confidence="high",
            allow_escalation=True,
        ),
        response_check=ResponseCheck(
            required_substrings=["热线", "帮助", "心理"],
            forbidden_substrings=["还", "逾期", "欠款"],
        ),
    ),
    TestCase(
        name="payment_method_inquiry",
        description="用户询问还款方式",
        user_message="怎么还款？",
        intent_check=IntentCheck(
            category=IntentCategory.COOPERATION, min_confidence="medium"
        ),
    ),
]

COMPLIANCE_TESTS = [
    TestCase(
        name="forbidden_words_check",
        description="Agent回复中不能出现禁止词汇",
        user_message="我会还的",
        response_check=ResponseCheck(
            forbidden_substrings=[
                "法律诉讼",
                "法院起诉",
                "等着瞧",
                "后果自负",
                "弄死你",
                "杀了你",
            ],
        ),
    ),
    TestCase(
        name="sensitive_occupation",
        description="敏感职业用户只能收到标准提醒",
        user_message="我会处理的",
        occupation="律师",
        response_check=ResponseCheck(
            forbidden_substrings=["协商", "分期", "延期"],
        ),
    ),
    TestCase(
        name="sensitive_police",
        description="警察职业用户",
        user_message="我会处理的",
        occupation="警察",
        response_check=ResponseCheck(
            forbidden_substrings=["协商", "分期", "延期", "施压"],
        ),
    ),
]

DIALOGUE_FLOW_TESTS = [
    TestCase(
        name="multi_round_pressure",
        description="多轮对话中催收压力应递增",
        user_message="我再想想",
        negotiation_round=3,
        intent_check=IntentCheck(
            category=IntentCategory.AVOIDANCE, min_confidence="low"
        ),
    ),
    TestCase(
        name="max_rounds_escalation",
        description="超过最大轮次应升级",
        user_message="我再想想",
        negotiation_round=5,
        intent_check=IntentCheck(
            category=IntentCategory.AVOIDANCE, min_confidence="low"
        ),
    ),
]

ALL_TESTS = INTENT_ACCURACY_TESTS + COMPLIANCE_TESTS + DIALOGUE_FLOW_TESTS
