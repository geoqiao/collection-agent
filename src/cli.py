import argparse
import asyncio
import logging

from src.core.constants import EventType
from src.core.models import Event, UserProfile, UserState
from src.main import CollectAgentSystem

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def run_demo(system: CollectAgentSystem) -> None:
    """Run a demo collection workflow."""
    user_id = "demo_user_001"

    # 1. Create an overdue user
    logger.info("=== Step 1: Create overdue user ===")
    state = UserState(
        user_id=user_id,
        profile=UserProfile(
            user_id=user_id,
            name="张三",
            phone="13800138000",
            overdue_days=5,
            amount_due=1000.0,
        ),
    )
    system.store.save(state)
    logger.info("Created user %s with overdue_days=5, amount_due=1000.0", user_id)

    # 2. Trigger scheduled outreach
    logger.info("=== Step 2: Trigger scheduled outreach ===")
    await system.run_scheduled_outreach()

    session = system.get_session(user_id)
    assert session is not None
    logger.info(
        "Session state after outreach: %s", session.state.session_state
    )

    # 3. Simulate user reply
    logger.info("=== Step 3: Simulate user reply ===")
    reply_event = Event(
        user_id=user_id,
        type=EventType.USER_REPLIED,
        payload={"channel": "chatbot", "content": "我会还的"},
    )
    await system.router.route_async(reply_event)
    logger.info(
        "Session state after reply: %s, intent: %s",
        session.state.session_state,
        session.state.conversation.current_intent,
    )

    # 4. Trigger follow-up (silence timeout re-engagement)
    logger.info("=== Step 4: Trigger follow-up ===")
    timeout_event = Event(
        user_id=user_id,
        type=EventType.SILENCE_TIMEOUT,
        payload={"tier": 0, "seconds": 600},
    )
    await system.router.route_async(timeout_event)
    logger.info(
        "Session state after follow-up: %s", session.state.session_state
    )

    # 5. Simulate payment
    logger.info("=== Step 5: Simulate payment ===")
    payment_event = Event(
        user_id=user_id,
        type=EventType.USER_PAYMENT_SUCCESS,
        payload={"amount": 1000.0},
    )
    await system.router.route_async(payment_event)
    logger.info(
        "Session state after payment: %s", session.state.session_state
    )

    # 6. Show final state
    logger.info("=== Final State ===")
    logger.info("User ID: %s", user_id)
    logger.info("Session State: %s", session.state.session_state)
    logger.info("Conversation Messages: %d", len(session.state.conversation.messages))
    for msg in session.state.conversation.messages:
        logger.info("  [%s] %s: %s", msg.channel, msg.direction, msg.content)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Debt Collection Agent")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument(
        "--action",
        choices=["scan", "event", "demo"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--user-id", help="User ID for event action")
    parser.add_argument("--event-type", help="Event type for event action")

    args = parser.parse_args()
    system = CollectAgentSystem.from_config(args.config)

    if args.action == "scan":
        await system.run_scheduled_outreach()
        await system.run_timeout_checks()
    elif args.action == "event":
        if not args.user_id or not args.event_type:
            parser.error("--user-id and --event-type are required for --action=event")
        event = Event(
            user_id=args.user_id,
            type=EventType[args.event_type],
        )
        await system.router.route_async(event)
    elif args.action == "demo":
        await run_demo(system)


if __name__ == "__main__":
    asyncio.run(main())
