"""User management and history tools."""

from __future__ import annotations

from typing import Any

from collect_agent.tools.base import Tool, ToolParameter, ToolResult


class QueryUserHistoryTool(Tool):
    name = "query_user_history"
    description = "Fetch the user's past contact and interaction history."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "interactions": [
                    {"date": "2025-04-01", "channel": "sms", "outcome": "no_response"},
                    {"date": "2025-04-05", "channel": "email", "outcome": "opened"},
                    {"date": "2025-04-10", "channel": "call", "outcome": "promised_to_pay"},
                ],
            },
        )


class AddToDncListTool(Tool):
    name = "add_to_dnc_list"
    description = "Add the user to the do-not-contact list."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
        ToolParameter(
            name="channel",
            param_type="string",
            description="Channel to block (all, sms, email, call).",
            required=False,
            enum=["all", "sms", "email", "call"],
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        channel = kwargs.get("channel", "all")
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "channel": channel,
                "status": "added_to_dnc",
                "effective_date": "2025-04-12",
            },
        )


class ScheduleReminderTool(Tool):
    name = "schedule_reminder"
    description = "Schedule a future outreach reminder for the user."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
        ToolParameter(
            name="remind_date",
            param_type="string",
            description="Date and time for the reminder (ISO 8601).",
            required=True,
        ),
        ToolParameter(
            name="channel",
            param_type="string",
            description="Channel for the reminder.",
            required=True,
            enum=["sms", "email", "whatsapp", "call"],
        ),
        ToolParameter(
            name="message",
            param_type="string",
            description="Reminder message content.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        remind_date = kwargs.get("remind_date", "2025-04-15T09:00:00Z")
        channel = kwargs.get("channel", "sms")
        message = kwargs.get("message", "")
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "remind_date": remind_date,
                "channel": channel,
                "message_preview": message[:50],
                "task_id": f"reminder-{user_id}-001",
                "status": "scheduled",
            },
        )
