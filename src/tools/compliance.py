"""Compliance and escalation tools."""

from __future__ import annotations

from typing import Any

from src.tools.base import Tool, ToolParameter, ToolResult


class PauseCollectionTool(Tool):
    name = "pause_collection"
    description = "Pause collection outreach for a specified period."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
        ToolParameter(
            name="days",
            param_type="number",
            description="Number of days to pause outreach.",
            required=True,
        ),
        ToolParameter(
            name="reason",
            param_type="string",
            description="Reason for pausing collection.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        days = kwargs.get("days", 7)
        reason = kwargs.get("reason", "user request")
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "paused_days": days,
                "reason": reason,
                "resume_date": "2025-04-19",
                "status": "paused",
            },
        )


class EscalateToHumanTool(Tool):
    name = "escalate_to_human"
    description = "Transfer the case to a human agent for manual handling."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
        ToolParameter(
            name="reason",
            param_type="string",
            description="Reason for escalation.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        reason = kwargs.get("reason", "user request")
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "reason": reason,
                "ticket_id": f"ticket-{user_id}-001",
                "status": "escalated",
            },
        )


class WelfareAlertTool(Tool):
    name = "welfare_alert"
    description = "Trigger a welfare/crisis alert for a user in distress."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
        ToolParameter(
            name="details",
            param_type="string",
            description="Details about the crisis or welfare concern.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        details = kwargs.get("details", "")
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "alert_id": f"alert-{user_id}-001",
                "details": details,
                "status": "alert_triggered",
                "notified_team": "welfare_support",
            },
        )
