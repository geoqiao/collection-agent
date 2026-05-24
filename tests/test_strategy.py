import pytest
from collect_agent.strategy.detector import IntentDetector
from collect_agent.strategy.engine import StrategyEngine
from collect_agent.core.constants import Intent
from collect_agent.core.models import UserProfile


@pytest.fixture
def detector():
    return IntentDetector()


def test_detect_willing(detector):
    assert detector.detect("我明天就还") == Intent.WILLING_TO_PAY
    assert detector.detect("我会处理的") == Intent.WILLING_TO_PAY


def test_detect_unwilling(detector):
    assert detector.detect("我没钱，不还了") == Intent.UNWILLING_TO_PAY
    assert detector.detect("不还") == Intent.UNWILLING_TO_PAY


def test_detect_complaint(detector):
    assert detector.detect("我要投诉你们") == Intent.COMPLAINT


def test_detect_payment_inquiry(detector):
    assert detector.detect("银行卡") == Intent.PAYMENT_METHOD_INQUIRY


def test_detect_operation_inquiry(detector):
    assert detector.detect("操作失败") == Intent.OPERATION_INQUIRY


def test_detect_ineffective_silence(detector):
    assert detector.detect("") == Intent.INEFFECTIVE_CONTACT
    assert detector.detect("嗯") == Intent.INEFFECTIVE_CONTACT


@pytest.fixture
def engine():
    return StrategyEngine()


def test_select_strategy_for_willing(engine):
    user = UserProfile(user_id="u001")
    strategy = engine.select_strategy(user, Intent.WILLING_TO_PAY)
    assert strategy["type"] == "confirm_plan"


def test_select_strategy_for_sensitive_user(engine):
    user = UserProfile(user_id="u001", occupation="律师")
    strategy = engine.select_strategy(user, Intent.UNWILLING_TO_PAY)
    assert strategy["type"] == "standard_reminder"


def test_select_strategy_for_complaint(engine):
    user = UserProfile(user_id="u001")
    strategy = engine.select_strategy(user, Intent.COMPLAINT)
    assert strategy["type"] == "pause_collection"


def test_get_response_for_willing(engine):
    user = UserProfile(user_id="u001", name="张三")
    resp = engine.get_response(user, {"type": "confirm_plan"}, {})
    assert "张三" in resp or "还款" in resp
