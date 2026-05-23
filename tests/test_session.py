import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.constants import (
    ChannelType,
    EventType,
    SessionState,
)
from src.core.models import Event, UserProfile, UserState
from src.session.session import CollectionSession


@pytest.fixture
def user_state():
    return UserState(
        user_id="u001",
        profile=UserProfile(user_id="u001", name="张三", amount_due=1000.0, overdue_days=5),
    )


@pytest.fixture
def mock_deps():
    return {
        "strategy_engine": MagicMock(),
        "orchestrator": MagicMock(),
        "quota_manager": MagicMock(),
        "compliance_checker": MagicMock(),
        "llm_client": AsyncMock(),
        "storage": MagicMock(),
    }


@pytest.mark.asyncio
async def test_handle_scheduled_outreach(user_state, mock_deps):
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["orchestrator"].can_contact_user.return_value = (True, "")
    mock_deps["orchestrator"].select_channel.return_value = ChannelType.CHATBOT
    mock_deps["orchestrator"].arbitrate.return_value = "granted"
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "re_engage"}
    mock_deps["llm_client"].generate_strategy_response.return_value = "您好张三，请尽快处理您的逾期账单。"

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)

    event = Event(user_id="u001", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    mock_deps["compliance_checker"].is_within_valid_hours.assert_called_once()
    mock_deps["orchestrator"].can_contact_user.assert_called_once()
    mock_deps["orchestrator"].select_channel.assert_called_once()
    mock_deps["orchestrator"].arbitrate.assert_called_once_with("u001", ChannelType.CHATBOT)
    mock_deps["strategy_engine"].select_strategy.assert_called_once()
    mock_deps["llm_client"].generate_strategy_response.assert_called_once()
    mock_deps["quota_manager"].record_chat.assert_called_once_with("u001")
    mock_deps["storage"].save.assert_called_once()

    assert session.state_machine.current == SessionState.INTENT_DETECTED
    assert session.state.session_state == "intent_detected"


@pytest.mark.asyncio
async def test_handle_user_replied(user_state, mock_deps):
    mock_deps["strategy_engine"].select_strategy.return_value = {"type": "confirm_plan"}
    mock_deps["llm_client"].generate_strategy_response.return_value = "感谢您愿意处理此事。"
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

    mock_deps["orchestrator"].arbitrate.assert_called_once_with("u001", ChannelType.VOICE)
    assert session.lock.holder == ChannelType.VOICE
    assert session.state_machine.current == SessionState.INTENT_DETECTED
    mock_deps["storage"].save.assert_called_once()


@pytest.mark.asyncio
async def test_handle_silence_timeout(user_state, mock_deps):
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["orchestrator"].can_contact_user.return_value = (True, "")
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
    mock_deps["orchestrator"].release_lock.assert_called_once_with("u001")
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
    mock_deps["orchestrator"].can_contact_user.return_value = (False, "Daily call limit reached")

    session = CollectionSession(user_id="u001", state=user_state, **mock_deps)

    event = Event(user_id="u001", type=EventType.SCHEDULED_OUTREACH)
    await session.handle_event(event)

    mock_deps["orchestrator"].select_channel.assert_not_called()
    mock_deps["storage"].save.assert_not_called()


@pytest.mark.asyncio
async def test_state_machine_transitions_on_events(user_state, mock_deps):
    mock_deps["compliance_checker"].is_within_valid_hours.return_value = True
    mock_deps["orchestrator"].can_contact_user.return_value = (True, "")
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

    await session.handle_event(Event(user_id="u001", type=EventType.USER_PAYMENT_SUCCESS))
    assert session.state_machine.current == SessionState.RESOLVED
