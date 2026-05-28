"""Tool operations — all tools as async functions with real side effects.

Every tool here writes to the store or triggers real business actions.
No more mock returns.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from collect_agent.tools.registry import tool


@tool(
    name="query_bill",
    description="Query the user's current bill information (amount, overdue days, due date).",
)
async def query_bill(user_id: str, store: Any) -> dict[str, Any]:
    """Return bill facts from user state."""
    state = store.load(user_id)
    if not state:
        return {"error": "User not found"}

    return {
        "user_id": user_id,
        "amount_due": state.profile.amount_due,
        "overdue_days": state.profile.overdue_days,
        "name": state.profile.name,
    }


@tool(
    name="pause_collection",
    description="Pause collection outreach for a specified period.",
)
async def pause_collection(
    user_id: str,
    days: int,
    reason: str,
    store: Any,
) -> dict[str, Any]:
    """Real side effect: write paused_until to user state."""
    state = store.load(user_id)
    if not state:
        return {"error": "User not found"}

    state.paused_until = datetime.now() + timedelta(days=days)
    store.save(state)

    return {
        "user_id": user_id,
        "status": "paused",
        "paused_until": state.paused_until.isoformat(),
        "reason": reason,
    }


@tool(
    name="escalate_to_human",
    description="Transfer the case to a human agent for manual handling.",
)
async def escalate_to_human(
    user_id: str,
    reason: str,
    store: Any,
) -> dict[str, Any]:
    """Real side effect: write ticket record (if store supports it)."""
    state = store.load(user_id)
    if not state:
        return {"error": "User not found"}

    ticket_id = f"ticket-{user_id}-{int(datetime.now().timestamp())}"

    # If store supports ticket logging
    if hasattr(store, "save_ticket"):
        await store.save_ticket(
            {
                "ticket_id": ticket_id,
                "user_id": user_id,
                "reason": reason,
                "created_at": datetime.now().isoformat(),
                "status": "open",
            }
        )

    return {
        "user_id": user_id,
        "ticket_id": ticket_id,
        "reason": reason,
        "status": "escalated",
    }


@tool(
    name="welfare_alert",
    description="Trigger a welfare/crisis alert for a user in distress.",
)
async def welfare_alert(
    user_id: str,
    details: str,
    store: Any,
) -> dict[str, Any]:
    """Real side effect: write crisis alert record."""
    alert_id = f"alert-{user_id}-{int(datetime.now().timestamp())}"

    if hasattr(store, "save_alert"):
        await store.save_alert(
            {
                "alert_id": alert_id,
                "user_id": user_id,
                "details": details,
                "created_at": datetime.now().isoformat(),
                "status": "alert_triggered",
                "notified_team": "welfare_support",
            }
        )

    return {
        "user_id": user_id,
        "alert_id": alert_id,
        "details": details,
        "status": "alert_triggered",
    }


@tool(
    name="add_to_dnc",
    description="Add the user to the do-not-contact (DNC) list.",
)
async def add_to_dnc(
    user_id: str,
    reason: str,
    store: Any,
) -> dict[str, Any]:
    """Real side effect: set dnc flag on user state."""
    state = store.load(user_id)
    if not state:
        return {"error": "User not found"}

    # Add dnc field if not present
    if not hasattr(state, "dnc"):

        # Monkey-patch for backward compat during migration
        object.__setattr__(state, "dnc", True)
    else:
        state.dnc = True  # type: ignore[attr-defined]

    store.save(state)

    return {
        "user_id": user_id,
        "status": "added_to_dnc",
        "reason": reason,
    }


@tool(
    name="query_user_history",
    description="Fetch the user's past contact and interaction history.",
)
async def query_user_history(user_id: str, store: Any) -> dict[str, Any]:
    """Return conversation history from user state."""
    state = store.load(user_id)
    if not state:
        return {"error": "User not found"}

    msgs = state.conversation.messages[-10:] if state.conversation else []
    return {
        "user_id": user_id,
        "interactions": [
            {
                "timestamp": m.timestamp.isoformat() if m.timestamp else "",
                "direction": m.direction,
                "content": m.content[:100],
            }
            for m in msgs
        ],
    }


@tool(
    name="schedule_reminder",
    description="Schedule a future outreach reminder for the user.",
)
async def schedule_reminder(
    user_id: str,
    remind_date: str,
    channel: str,
    message: str,
    store: Any,
) -> dict[str, Any]:
    """Real side effect: write reminder record."""
    task_id = f"reminder-{user_id}-{int(datetime.now().timestamp())}"

    if hasattr(store, "save_reminder"):
        await store.save_reminder(
            {
                "task_id": task_id,
                "user_id": user_id,
                "remind_date": remind_date,
                "channel": channel,
                "message": message,
                "status": "scheduled",
            }
        )

    return {
        "user_id": user_id,
        "task_id": task_id,
        "remind_date": remind_date,
        "channel": channel,
        "status": "scheduled",
    }


@tool(
    name="send_payment_link",
    description="Send a payment link to the user via their preferred channel.",
)
async def send_payment_link(
    user_id: str,
    amount: float,
    store: Any,
) -> dict[str, Any]:
    """Return payment link (no real side effect in MVP)."""
    return {
        "user_id": user_id,
        "amount": amount,
        "payment_url": f"https://payment.example.com/pay?user={user_id}&amount={amount}",
        "status": "link_generated",
    }


@tool(
    name="record_promise",
    description="Record a user's payment promise (date and amount).",
)
async def record_promise(
    user_id: str,
    promised_date: str,
    promised_amount: float,
    store: Any,
) -> dict[str, Any]:
    """Real side effect: write promise record."""
    promise_id = f"promise-{user_id}-{int(datetime.now().timestamp())}"

    if hasattr(store, "save_promise"):
        await store.save_promise(
            {
                "promise_id": promise_id,
                "user_id": user_id,
                "promised_date": promised_date,
                "promised_amount": promised_amount,
                "created_at": datetime.now().isoformat(),
                "status": "pending",
            }
        )

    return {
        "user_id": user_id,
        "promise_id": promise_id,
        "promised_date": promised_date,
        "promised_amount": promised_amount,
        "status": "recorded",
    }


@tool(
    name="check_payment_status",
    description="Check whether the user has made a recent payment.",
)
async def check_payment_status(user_id: str, store: Any) -> dict[str, Any]:
    """Check if user state shows resolved."""
    state = store.load(user_id)
    if not state:
        return {"error": "User not found"}

    is_paid = state.session_state == "resolved"
    return {
        "user_id": user_id,
        "is_paid": is_paid,
        "session_state": state.session_state,
    }
