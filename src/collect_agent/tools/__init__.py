"""Tools package — exports all tool operations and the registry."""

from __future__ import annotations

from collect_agent.tools.ops import (
    add_to_dnc,
    check_payment_status,
    escalate_to_human,
    pause_collection,
    query_bill,
    query_user_history,
    record_promise,
    schedule_reminder,
    send_payment_link,
    welfare_alert,
)
from collect_agent.tools.registry import ToolRegistry, get_registry, tool

__all__ = [
    "ToolRegistry",
    "get_registry",
    "tool",
    "query_bill",
    "pause_collection",
    "escalate_to_human",
    "welfare_alert",
    "add_to_dnc",
    "query_user_history",
    "schedule_reminder",
    "send_payment_link",
    "record_promise",
    "check_payment_status",
]
