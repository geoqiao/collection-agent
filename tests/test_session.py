from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from collect_agent.core.constants import (
    ChannelType,
    EventType,
    SessionState,
)
from collect_agent.core.models import Event, UserProfile, UserState
from collect_agent.session.session import CollectionSession


@pytest.fixture
def user_state():
    return UserState(
        user_id="u001",
        profile=UserProfile(
            user_id="u001", name="张三", amount_due=1000.0, overdue_days=5
        ),
    )


class MockOrchestrator:
    def __init__(self):
        self.is_within_compliance_hours = MagicMock(return_value=(True, ""))
        self.select_channel = AsyncMock(return_value=ChannelType.CHATBOT)
        self.arbitrate = AsyncMock(return_value="granted")
        lock_mock = MagicMock()
        lock_mock.acquire = MagicMock()
        lock_mock.release = MagicMock()
        lock_mock.holder = None
        lock_mock.is_locked = False
        self.get_lock = AsyncMock(return_value=lock_mock)
        self.release_and_cleanup_lock = MagicMock()


@pytest.fixture
def mock_deps():
    orchestrator = MockOrchestrator()
    quota_manager = AsyncMock()
    quota_manager.get_usage_for_user = MagicMock(return_value=None)

    return {
        "strategy_engine": MagicMock(),
        "orchestrator": orchestrator,
        "quota_manager": quota_manager,
        "compliance_checker": MagicMock(),
        "llm_client": AsyncMock(),
        "storage": MagicMock(),
    }


@pytest.mark.asyncio
async def test_handle_scheduled_outreach(user_state, mock_deps):
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["orchestrator"].is_within_compliance_hours.return_value = (True, "")
    mock_deps["orchestrator"].select_channel.return_value = ChannelType.CHATBOT
    mock_deps["orchestrator"].arbitrate.return_value = "granted"
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "re_engage"}
    mock_deps[
        "llm_client"
    ].generate_strategy_response.return_value = "您好张三，请尽快处理您的逾期账单。"

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)

    event = Event(user_id="u001", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    mock_deps["compliance_checker"].is_within_valid_hours.assert_called_once()
    mock_deps["orchestrator"].is_within_compliance_hours.assert_called_once()
    mock_deps["orchestrator"].select_channel.assert_called_once()
    mock_deps["orchestrator"].arbitrate.assert_called_once_with(
        "u001", ChannelType.CHATBOT
    )
    mock_deps["strategy_engine"].select_strategy.assert_called_once()
    mock_deps["llm_client"].generate_strategy_response.assert_called_once()
    mock_deps["quota_manager"].record_chat.assert_awaited_once_with("u001")
    mock_deps["storage"].save.assert_called_once()

    assert session.state_machine.current == SessionState.INTENT_DETECTED
    assert session.state.session_state == "intent_detected"


@pytest.mark.asyncio
async def test_handle_user_replied(user_state, mock_deps):
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "confirm_plan"}
    mock_deps[
        "llm_client"
    ].generate_strategy_response.return_value = "感谢您愿意处理此事。"
    mock_deps["llm_client"].detect_intent.return_value = "willing_to_pay"

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)

    event = Event(
        user_id="u001",
        type=EventType.USER_REPLIED,
        payload={"content": "我还", "channel": "chatbot"},
    )
    await session.handle_event(event)

    assert session.state.conversation.current_intent == "willing_to_pay"
    assert len(session.state.conversation.messages) == 1
    assert session.state.conversation.messages[0].direction == "inbound"
    assert session.state.conversation.messages[0].content == "我还"
    assert session.state.conversation.negotiation_round == 1
    mock_deps["storage"].save.assert_called_once()


@pytest.mark.asyncio
async def test_handle_call_connected(user_state, mock_deps):
    mock_deps["orchestrator"].arbitrate.return_value = "granted"

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)
    # First transition to OUTREACH_START so CALL_CONNECTED can go to INTENT_DETECTED
    session.state_machine.transition(SessionState.OUTREACH_START)

    event = Event(
        user_id="u001",
        type=EventType.CALL_CONNECTED,
        payload={"channel": "voice"},
    )
    await session.handle_event(event)

    mock_deps["orchestrator"].arbitrate.assert_called_once_with(
        "u001", ChannelType.VOICE
    )
    mock_deps["orchestrator"].get_lock.assert_awaited_once()
    assert session.state_machine.current == SessionState.INTENT_DETECTED
    mock_deps["storage"].save.assert_called_once()


@pytest.mark.asyncio
async def test_handle_silence_timeout(user_state, mock_deps):
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["orchestrator"].is_within_compliance_hours.return_value = (True, "")
    mock_deps["orchestrator"].arbitrate.return_value = "granted"
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "re_engage"}
    mock_deps["llm_client"].generate_strategy_response.return_value = "重新联系"

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)

    event = Event(user_id="u001", type=EventType.SILENCE_TIMEOUT)
    await session.handle_event(event)

    assert session.state.conversation.current_intent == "ineffective_contact"
    mock_deps["storage"].save.assert_called_once()


@pytest.mark.asyncio
async def test_handle_payment_success(user_state, mock_deps):
    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)
    # Need to reach INTENT_DETECTED before we can transition to RESOLVED
    session.state_machine.transition(SessionState.OUTREACH_START)
    session.state_machine.transition(SessionState.INTENT_DETECTED)

    event = Event(user_id="u001", type=EventType.USER_PAYMENT_SUCCESS)
    await session.handle_event(event)

    assert session.state_machine.current == SessionState.RESOLVED
    assert session.state.session_state == "resolved"
    mock_deps["orchestrator"].release_and_cleanup_lock.assert_called_once_with("u001")
    mock_deps["storage"].save.assert_called_once()


@pytest.mark.asyncio
async def test_compliance_blocks_outside_hours(user_state, mock_deps):
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = False

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)

    event = Event(user_id="u001", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    mock_deps["orchestrator"].select_channel.assert_not_called()
    mock_deps["storage"].save.assert_not_called()


@pytest.mark.asyncio
async def test_quota_limits_enforced(user_state, mock_deps):
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["orchestrator"].is_within_compliance_hours.return_value = (
        False,
        "Daily call limit reached",
    )

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)

    event = Event(user_id="u001", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    mock_deps["orchestrator"].select_channel.assert_not_called()
    mock_deps["storage"].save.assert_not_called()


@pytest.mark.asyncio
async def test_state_machine_transitions_on_events(user_state, mock_deps):
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["orchestrator"].is_within_compliance_hours.return_value = (True, "")
    mock_deps["orchestrator"].select_channel.return_value = ChannelType.CHATBOT
    mock_deps["orchestrator"].arbitrate.return_value = "granted"
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "re_engage"}
    mock_deps["llm_client"].generate_strategy_response.return_value = "test"

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)

    assert session.state_machine.current == SessionState.IDLE

    await session.handle_event(Event(user_id="u001", type=EventType.SCHEDULED_OUTREACH))
    assert session.state_machine.current == SessionState.INTENT_DETECTED

    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "confirm_plan"}
    mock_deps["llm_client"].detect_intent.return_value = "willing_to_pay"
    mock_deps["llm_client"].generate_strategy_response.return_value = "followup"

    await session.handle_event(
        Event(
            user_id="u001",
            type=EventType.USER_REPLIED,
            payload={"content": "明天还", "channel": "chatbot"},
        )
    )
    assert session.state_machine.current == SessionState.FOLLOW_UP

    await session.handle_event(
        Event(user_id="u001", type=EventType.USER_PAYMENT_SUCCESS)
    )
    assert session.state_machine.current == SessionState.RESOLVED


# ---------------------------------------------------------------------------
# Business logic gap tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sensitive_occupation_gets_standard_reminder_on_outreach(mock_deps):
    """Sensitive occupation user gets standard_reminder on first outreach."""
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["orchestrator"].is_within_compliance_hours.return_value = (True, "")
    mock_deps["orchestrator"].select_channel.return_value = ChannelType.CHATBOT
    mock_deps["orchestrator"].arbitrate.return_value = "granted"
    mock_deps["llm_client"].generate_strategy_response.return_value = "标准提醒"

    from collect_agent.strategy.strategies import STRATEGIES

    sensitive_state = UserState(
        user_id="u_lawyer",
        profile=UserProfile(
            user_id="u_lawyer",
            name="律师张",
            occupation="律师",
            amount_due=1000.0,
            overdue_days=5,
        ),
    )
    session = CollectionSession(user_id="u_lawyer", state=sensitive_state, **mock_deps)

    event = Event(user_id="u_lawyer", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    # Strategy engine should NOT be called for sensitive users
    mock_deps["strategy_engine"].select_strategy.assert_not_called()
    # LLM should still be called with standard_reminder strategy
    mock_deps["llm_client"].generate_strategy_response.assert_awaited_once()
    call_args = mock_deps["llm_client"].generate_strategy_response.call_args
    assert call_args[0][0] == STRATEGIES["standard_reminder"]


@pytest.mark.asyncio
async def test_sensitive_occupation_gets_standard_reminder_on_reply(mock_deps):
    """Sensitive occupation user gets standard_reminder on reply."""
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["llm_client"].generate_strategy_response.return_value = "标准提醒"
    mock_deps["llm_client"].detect_intent.return_value = "willing_to_pay"

    from collect_agent.strategy.strategies import STRATEGIES

    sensitive_state = UserState(
        user_id="u_lawyer",
        profile=UserProfile(
            user_id="u_lawyer",
            name="律师张",
            occupation="律师",
            amount_due=1000.0,
            overdue_days=5,
        ),
    )
    session = CollectionSession(user_id="u_lawyer", state=sensitive_state, **mock_deps)

    event = Event(
        user_id="u_lawyer",
        type=EventType.USER_REPLIED,
        payload={"content": "我会还的", "channel": "chatbot"},
    )
    await session.handle_event(event)

    # Strategy engine should NOT be called for sensitive users
    mock_deps["strategy_engine"].select_strategy.assert_not_called()
    call_args = mock_deps["llm_client"].generate_strategy_response.call_args
    assert call_args[0][0] == STRATEGIES["standard_reminder"]


@pytest.mark.asyncio
async def test_complaint_event_pauses_collection(mock_deps):
    """COMPLAINT event pauses collection for 48 hours."""
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["llm_client"].generate_strategy_response.return_value = "抱歉，已转客服"

    state = UserState(
        user_id="u_complaint",
        profile=UserProfile(
            user_id="u_complaint", name="投诉者", amount_due=1000.0, overdue_days=5
        ),
    )
    session = CollectionSession(user_id="u_complaint", state=state, **mock_deps)
    # Need to reach INTENT_DETECTED before RESOLVED
    session.state_machine.transition(SessionState.OUTREACH_START)
    session.state_machine.transition(SessionState.INTENT_DETECTED)

    event = Event(user_id="u_complaint", type=EventType.COMPLAINT)
    await session.handle_event(event)

    assert session.state.paused_until is not None
    from datetime import datetime, timedelta

    now = datetime.now(UTC)
    assert session.state.paused_until > now + timedelta(hours=47)
    assert session.state.paused_until < now + timedelta(hours=49)
    assert session.state_machine.current == SessionState.RESOLVED
    mock_deps["storage"].save.assert_called_once()


@pytest.mark.asyncio
async def test_max_rounds_enforcement(mock_deps):
    """Max rounds reached escalates to complaint/standard reminder."""
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["strategy_engine"].select_strategy.return_value = {
        "type": "confirm_plan",
        "max_rounds": 2,
    }
    mock_deps["llm_client"].generate_strategy_response.return_value = "followup"
    mock_deps["llm_client"].detect_intent.return_value = "willing_to_pay"

    state = UserState(
        user_id="u_max",
        profile=UserProfile(
            user_id="u_max", name="用户", amount_due=1000.0, overdue_days=5
        ),
    )
    state.conversation.negotiation_round = 2
    session = CollectionSession(user_id="u_max", state=state, **mock_deps)

    event = Event(
        user_id="u_max",
        type=EventType.USER_REPLIED,
        payload={"content": "明天还", "channel": "chatbot"},
    )
    await session.handle_event(event)

    # After increment, round=3 >= max_rounds=2, should escalate
    assert session.state.conversation.negotiation_round == 3
    # Should escalate to COMPLAINT strategy (or standard_reminder fallback)
    from collect_agent.core.constants import Intent
    from collect_agent.strategy.strategies import STRATEGIES

    call_args = mock_deps["llm_client"].generate_strategy_response.call_args
    assert call_args[0][0] == STRATEGIES[Intent.COMPLAINT]


@pytest.mark.asyncio
async def test_quota_adjustment_on_user_reply(mock_deps):
    """Quota manager set_chat_replied called on USER_REPLIED."""
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "confirm_plan"}
    mock_deps["llm_client"].generate_strategy_response.return_value = "感谢"
    mock_deps["llm_client"].detect_intent.return_value = "willing_to_pay"

    state = UserState(
        user_id="u_quota",
        profile=UserProfile(
            user_id="u_quota", name="用户", amount_due=1000.0, overdue_days=5
        ),
    )
    session = CollectionSession(user_id="u_quota", state=state, **mock_deps)

    event = Event(
        user_id="u_quota",
        type=EventType.USER_REPLIED,
        payload={"content": "我会还的", "channel": "chatbot"},
    )
    await session.handle_event(event)

    mock_deps["quota_manager"].set_chat_replied.assert_awaited_once_with("u_quota")


@pytest.mark.asyncio
async def test_content_audit_blocks_forbidden_words(mock_deps):
    """Content audit blocks messages with forbidden words."""
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["compliance_checker"].audit_content.return_value = (
        False,
        "Content contains forbidden words",
    )
    mock_deps["compliance_checker"].get_standard_message.return_value = "标准消息"
    mock_deps["orchestrator"].is_within_compliance_hours.return_value = (True, "")
    mock_deps["orchestrator"].select_channel.return_value = ChannelType.CHATBOT
    mock_deps["orchestrator"].arbitrate.return_value = "granted"
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "re_engage"}
    mock_deps[
        "llm_client"
    ].generate_strategy_response.return_value = "包含法律诉讼的内容"

    state = UserState(
        user_id="u_audit",
        profile=UserProfile(
            user_id="u_audit", name="用户", amount_due=1000.0, overdue_days=5
        ),
    )
    session = CollectionSession(user_id="u_audit", state=state, **mock_deps)

    event = Event(user_id="u_audit", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    mock_deps["compliance_checker"].audit_content.assert_called_once_with(
        "包含法律诉讼的内容"
    )
    mock_deps["compliance_checker"].get_standard_message.assert_called_once_with(
        state.profile
    )


# ---------------------------------------------------------------------------
# State sync tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_sync_includes_quota_usage_and_conversation(mock_deps):
    """_sync_state includes quota_usage and conversation current_intent."""
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["orchestrator"].is_within_compliance_hours.return_value = (True, "")
    mock_deps["orchestrator"].select_channel.return_value = ChannelType.CHATBOT
    mock_deps["orchestrator"].arbitrate.return_value = "granted"
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "re_engage"}
    mock_deps["llm_client"].generate_strategy_response.return_value = "test"

    # Use real QuotaManager so _usages is populated
    from collect_agent.quota.manager import QuotaManager

    quota_manager = QuotaManager()
    mock_deps["quota_manager"] = quota_manager

    state = UserState(
        user_id="u_sync",
        profile=UserProfile(
            user_id="u_sync", name="用户", amount_due=1000.0, overdue_days=5
        ),
    )
    session = CollectionSession(user_id="u_sync", state=state, **mock_deps)

    event = Event(user_id="u_sync", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    assert session.state.quota_usage != {}
    assert session.state.quota_usage["chat_sent_count"] == 1
    # After outreach, current_intent is not set yet (only set on interaction)
    assert session.state.conversation.current_intent is None


# ---------------------------------------------------------------------------
# Exception handling tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_violation_caught_separately(user_state, mock_deps):
    """ComplianceViolationError is caught separately in handle_event."""
    from collect_agent.core.exceptions import ComplianceViolationError

    # Make _handle_outreach_event raise ComplianceViolationError
    async def raise_compliance(*args, **kwargs):
        raise ComplianceViolationError("outside valid hours")

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)
    original_handler = session._handle_outreach_event
    session._handle_outreach_event = raise_compliance

    event = Event(user_id="u001", type=EventType.SCHEDULED_OUTREACH)
    # Should not raise, just log
    await session.handle_event(event)

    session._handle_outreach_event = original_handler


# ---------------------------------------------------------------------------
# Config from_dict tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_config_from_dict_works_correctly():
    """QuotaProfile.from_dict and ComplianceRules.from_dict filter unknown keys."""
    from collect_agent.compliance.rules import ComplianceRules
    from collect_agent.quota.profile import QuotaProfile

    quota = QuotaProfile.from_dict(
        {
            "call_self_daily_max": 5,
            "unknown_key": "should_be_ignored",
        }
    )
    assert quota.call_self_daily_max == 5
    assert quota.call_contact_daily_max == 10  # default

    rules = ComplianceRules.from_dict(
        {
            "valid_hours": [9, 18],
            "max_call_per_hour": 5,
            "unknown_key": "should_be_ignored",
        }
    )
    assert rules.valid_hours == (9, 18)
    assert rules.max_call_per_hour == 5
    assert rules.min_call_interval_minutes == 10  # default


# ---------------------------------------------------------------------------
# Silence timeout outreach tracking tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_silence_timeout_uses_outreach_time(mock_deps):
    """SilenceTimeoutTracker uses last_outreach_at, not last_interaction_at."""
    from datetime import datetime
    from unittest.mock import patch

    from collect_agent.session.timeout_tracker import SilenceTimeoutTracker

    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["orchestrator"].is_within_compliance_hours.return_value = (True, "")
    mock_deps["orchestrator"].arbitrate.return_value = "granted"
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "re_engage"}
    mock_deps["llm_client"].generate_strategy_response.return_value = "test"

    state = UserState(
        user_id="u_timeout",
        profile=UserProfile(
            user_id="u_timeout", name="用户", amount_due=1000.0, overdue_days=5
        ),
    )
    session = CollectionSession(user_id="u_timeout", state=state, **mock_deps)

    # Trigger outreach to set last_outreach_at
    event = Event(user_id="u_timeout", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    assert session.last_outreach_at is not None
    assert session.last_interaction_at is None  # outreach does not set interaction

    tracker = SilenceTimeoutTracker()

    # 11 minutes after outreach
    future = session.last_outreach_at.replace(
        minute=(session.last_outreach_at.minute + 11) % 60,
        second=0,
        microsecond=0,
    )
    if future.minute < session.last_outreach_at.minute:
        future = future.replace(hour=future.hour + 1)

    with patch("collect_agent.session.timeout_tracker.datetime") as mock_dt:
        mock_dt.now.return_value = future
        mock_dt.side_effect = lambda tz=None: datetime.now(tz) if tz else datetime.now()
        tier = await tracker.check_timeout(session)
        assert tier == 0


# ---------------------------------------------------------------------------
# Channel receive updates state tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_channel_receive_updates_state_on_user_replied(mock_deps):
    """USER_REPLIED calls channel.receive and updates channel state."""
    from collect_agent.channels.chatbot import ChatbotChannel
    from collect_agent.core.constants import ChannelState

    mock_deps["compliance_checker"].audit_content.return_value = (True, "")
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "confirm_plan"}
    mock_deps["llm_client"].generate_strategy_response.return_value = "感谢"
    mock_deps["llm_client"].detect_intent.return_value = "willing_to_pay"

    state = UserState(
        user_id="u_receive",
        profile=UserProfile(
            user_id="u_receive", name="用户", amount_due=1000.0, overdue_days=5
        ),
    )
    session = CollectionSession(user_id="u_receive", state=state, **mock_deps)

    # Replace chatbot channel with real one to track receive
    real_chatbot = ChatbotChannel()
    session.channels._channels[ChannelType.CHATBOT] = real_chatbot
    # Set both registry and internal state to WAITING_REPLY so receive transitions to INTERACTING
    session.channels._states[ChannelType.CHATBOT] = ChannelState.WAITING_REPLY
    real_chatbot._states["u_receive"] = ChannelState.WAITING_REPLY

    event = Event(
        user_id="u_receive",
        type=EventType.USER_REPLIED,
        payload={"content": "我会还的", "channel": "chatbot"},
    )
    await session.handle_event(event)

    # The real chatbot channel's internal state should be INTERACTING after receive()
    assert real_chatbot._get_state("u_receive") == ChannelState.INTERACTING
