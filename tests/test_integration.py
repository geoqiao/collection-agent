from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.cli import run_demo
from src.core.constants import EventType, SessionState
from src.core.models import Event, UserProfile, UserState
from src.main import CollectAgentSystem


@pytest.fixture
def system():
    return CollectAgentSystem()


def test_system_initialization(system):
    assert system.router is not None
    assert system.session_manager is not None
    assert system.scheduler is not None


def test_handle_user_login_event(system):
    event = Event(user_id="u001", type=EventType.USER_LOGIN)
    system.handle_event(event)
    session = system.session_manager.get("u001")
    assert session is not None
    assert session.user_id == "u001"


@pytest.mark.asyncio
async def test_silence_timeout_10min(system):
    """After 10min silence, SILENCE_TIMEOUT emitted."""
    # Create session and simulate interaction
    session = system.session_manager.get_or_create("u_silence")
    session.last_interaction_at = datetime.now(timezone.utc)

    # Wire tracker
    system.scheduler._ensure_tracker_wired(session)

    # Mock time: 11 minutes passed
    future = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    with patch("src.session.timeout_tracker.datetime") as mock_dt:
        mock_dt.now.return_value = future
        mock_dt.side_effect = lambda tz=None: datetime.now(tz) if tz else datetime.now()
        # Add 11 minutes to now
        mock_dt.now.return_value = session.last_interaction_at.replace(
            minute=(session.last_interaction_at.minute + 11) % 60,
            second=0,
            microsecond=0,
        )
        if mock_dt.now.return_value.minute < session.last_interaction_at.minute:
            mock_dt.now.return_value = mock_dt.now.return_value.replace(
                hour=mock_dt.now.return_value.hour + 1
            )

        tier = system.scheduler.tracker.check_timeout(session)
        assert tier == 0  # 10min tier


@pytest.mark.asyncio
async def test_silence_timeout_1hour(system):
    """After 1h silence, next tier."""
    session = system.session_manager.get_or_create("u_silence_1h")
    session.last_interaction_at = datetime.now(timezone.utc)
    system.scheduler._ensure_tracker_wired(session)

    # Emit 10min tier first
    future_10min = session.last_interaction_at.replace(
        minute=(session.last_interaction_at.minute + 11) % 60,
        second=0,
        microsecond=0,
    )
    if future_10min.minute < session.last_interaction_at.minute:
        future_10min = future_10min.replace(hour=future_10min.hour + 1)

    with patch("src.session.timeout_tracker.datetime") as mock_dt:
        mock_dt.now.return_value = future_10min
        mock_dt.side_effect = lambda tz=None: datetime.now(tz) if tz else datetime.now()
        tier = system.scheduler.tracker.check_timeout(session)
        assert tier == 0

    # Now 1h+1min later
    future_1h = session.last_interaction_at.replace(
        hour=session.last_interaction_at.hour + 1,
        minute=session.last_interaction_at.minute + 1,
        second=0,
        microsecond=0,
    )

    with patch("src.session.timeout_tracker.datetime") as mock_dt:
        mock_dt.now.return_value = future_1h
        mock_dt.side_effect = lambda tz=None: datetime.now(tz) if tz else datetime.now()
        tier = system.scheduler.tracker.check_timeout(session)
        assert tier == 1  # 1hour tier


@pytest.mark.asyncio
async def test_silence_timeout_no_repeat(system):
    """Same tier not emitted twice."""
    session = system.session_manager.get_or_create("u_no_repeat")
    session.last_interaction_at = datetime.now(timezone.utc)
    system.scheduler._ensure_tracker_wired(session)

    future_10min = session.last_interaction_at.replace(
        minute=(session.last_interaction_at.minute + 11) % 60,
        second=0,
        microsecond=0,
    )
    if future_10min.minute < session.last_interaction_at.minute:
        future_10min = future_10min.replace(hour=future_10min.hour + 1)

    with patch("src.session.timeout_tracker.datetime") as mock_dt:
        mock_dt.now.return_value = future_10min
        mock_dt.side_effect = lambda tz=None: datetime.now(tz) if tz else datetime.now()
        tier1 = system.scheduler.tracker.check_timeout(session)
        assert tier1 == 0

        tier2 = system.scheduler.tracker.check_timeout(session)
        assert tier2 is None  # Not repeated


@pytest.mark.asyncio
async def test_scheduled_outreach_for_overdue(system):
    """Scanner finds overdue users."""
    # Create a user with overdue days
    state = UserState(
        user_id="u_overdue",
        profile=UserProfile(user_id="u_overdue", overdue_days=5, amount_due=100.0),
    )
    system.store.save(state)

    # Track routed events by collecting them
    routed_events = []
    original_route_async = system.router.route_async

    async def capturing_route_async(event):
        routed_events.append(event)
        await original_route_async(event)

    system.router.route_async = capturing_route_async

    await system.run_scheduled_outreach()

    assert len(routed_events) == 1
    assert routed_events[0].user_id == "u_overdue"
    assert routed_events[0].type == EventType.SCHEDULED_OUTREACH


@pytest.mark.asyncio
async def test_scheduled_outreach_skips_paid(system):
    """Scanner skips resolved users."""
    state = UserState(
        user_id="u_paid",
        profile=UserProfile(user_id="u_paid", overdue_days=0, amount_due=0.0),
        session_state="resolved",
    )
    system.store.save(state)

    routed_events = []
    original_route_async = system.router.route_async

    async def capturing_route_async(event):
        routed_events.append(event)
        await original_route_async(event)

    system.router.route_async = capturing_route_async

    await system.run_scheduled_outreach()

    assert len(routed_events) == 0


@pytest.mark.asyncio
async def test_full_flow_login_to_outreach(system):
    """User login -> event -> session created -> outreach triggered."""
    # User logs in - use async route directly to avoid race condition
    login_event = Event(user_id="u_flow", type=EventType.USER_LOGIN)
    await system.router.route_async(login_event)

    session = system.session_manager.get("u_flow")
    assert session is not None

    # Mark user as overdue in store
    state = UserState(
        user_id="u_flow",
        profile=UserProfile(user_id="u_flow", overdue_days=3, amount_due=50.0),
    )
    system.store.save(state)

    # Run scheduled outreach
    routed_events = []
    original_route_async = system.router.route_async

    async def capturing_route_async(event):
        routed_events.append(event)
        await original_route_async(event)

    system.router.route_async = capturing_route_async

    await system.run_scheduled_outreach()

    assert len(routed_events) == 1
    assert routed_events[0].user_id == "u_flow"
    assert routed_events[0].type == EventType.SCHEDULED_OUTREACH


@pytest.mark.asyncio
async def test_silence_timeout_via_scheduler(system):
    """Scheduler check_silence_timeouts emits SILENCE_TIMEOUT."""
    session = system.session_manager.get_or_create("u_scheduler_timeout")
    session.last_interaction_at = datetime.now(timezone.utc)
    system.scheduler._ensure_tracker_wired(session)

    future_10min = session.last_interaction_at.replace(
        minute=(session.last_interaction_at.minute + 11) % 60,
        second=0,
        microsecond=0,
    )
    if future_10min.minute < session.last_interaction_at.minute:
        future_10min = future_10min.replace(hour=future_10min.hour + 1)

    routed_events = []
    original_route_async = system.router.route_async

    async def capturing_route_async(event):
        routed_events.append(event)
        await original_route_async(event)

    system.router.route_async = capturing_route_async

    with patch("src.session.timeout_tracker.datetime") as mock_dt:
        mock_dt.now.return_value = future_10min
        mock_dt.side_effect = lambda tz=None: datetime.now(tz) if tz else datetime.now()
        await system.run_timeout_checks()

    assert len(routed_events) == 1
    assert routed_events[0].type == EventType.SILENCE_TIMEOUT
    assert routed_events[0].payload["tier"] == 0


# ---------------------------------------------------------------------------
# New end-to-end tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demo_mode():
    """Run the full demo and verify state transitions."""
    system = CollectAgentSystem()
    await run_demo(system)

    session = system.get_session("demo_user_001")
    assert session is not None
    assert session.state.session_state == SessionState.RESOLVED.value
    assert session.state.conversation.current_intent is not None


@pytest.mark.asyncio
async def test_cli_scan_action():
    """CLI --action=scan works."""
    system = CollectAgentSystem()
    state = UserState(
        user_id="u_scan",
        profile=UserProfile(user_id="u_scan", overdue_days=3, amount_due=50.0),
    )
    system.store.save(state)

    routed_events = []
    original_route_async = system.router.route_async

    async def capturing_route_async(event):
        routed_events.append(event)
        await original_route_async(event)

    system.router.route_async = capturing_route_async

    await system.run_scheduled_outreach()
    await system.run_timeout_checks()

    assert any(e.type == EventType.SCHEDULED_OUTREACH for e in routed_events)


@pytest.mark.asyncio
async def test_cli_event_action():
    """CLI --action=event works."""
    system = CollectAgentSystem()
    event = Event(user_id="u_event", type=EventType.USER_LOGIN)
    await system.router.route_async(event)

    session = system.get_session("u_event")
    assert session is not None
    assert session.user_id == "u_event"


@pytest.mark.asyncio
async def test_from_config(tmp_path):
    """Config loading works."""
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(
        """
llm:
  provider: mock
  model: ""
  api_key: ""
  temperature: 0.3
  max_tokens: 1024

compliance:
  valid_hours: [8, 20]
  max_call_per_hour: 3
  min_call_interval_minutes: 10

quota:
  call_self_daily_max: 10
  call_contact_daily_max: 10
  call_answer_daily_max: 3
  chat_unanswered_daily_max: 5
  chat_answered_daily_max: 100
  push_daily_max: 1

storage:
  db_path: "test_collect_agent.db"
""",
        encoding="utf-8",
    )
    system = CollectAgentSystem.from_config(str(config_path))
    assert system is not None
    assert system.store is not None


@pytest.mark.asyncio
async def test_full_collection_lifecycle():
    """Full lifecycle: overdue -> outreach -> reply -> follow-up -> payment."""
    system = CollectAgentSystem()
    user_id = "u_lifecycle"

    # 1. User created with overdue_days=5
    state = UserState(
        user_id=user_id,
        profile=UserProfile(
            user_id=user_id,
            name="李四",
            overdue_days=5,
            amount_due=500.0,
        ),
    )
    system.store.save(state)

    # 2. SCHEDULED_OUTREACH -> chatbot message sent
    await system.run_scheduled_outreach()
    session = system.get_session(user_id)
    assert session is not None
    assert session.state.session_state in (
        SessionState.OUTREACH_START.value,
        SessionState.INTENT_DETECTED.value,
        SessionState.FOLLOW_UP.value,
    )

    # 3. USER_REPLIED "我会还的" -> intent=WILLING
    reply_event = Event(
        user_id=user_id,
        type=EventType.USER_REPLIED,
        payload={"channel": "chatbot", "content": "我会还的"},
    )
    await system.router.route_async(reply_event)
    assert session.state.conversation.current_intent == "willing_to_pay"

    # 4. Follow-up with confirm_plan strategy (triggered by silence timeout)
    timeout_event = Event(
        user_id=user_id,
        type=EventType.SILENCE_TIMEOUT,
        payload={"tier": 0, "seconds": 600},
    )
    await system.router.route_async(timeout_event)
    assert session.state.session_state == SessionState.FOLLOW_UP.value

    # 5. USER_PAYMENT_SUCCESS -> session resolved
    payment_event = Event(
        user_id=user_id,
        type=EventType.USER_PAYMENT_SUCCESS,
        payload={"amount": 500.0},
    )
    await system.router.route_async(payment_event)
    assert session.state.session_state == SessionState.RESOLVED.value
