"""Payment promise and status tools."""

from __future__ import annotations

from typing import Any

from collect_agent.tools.base import Tool, ToolParameter, ToolResult


class RecordPromiseTool(Tool):
    name = "record_promise"
    description = "Log a payment promise made by the user."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
        ToolParameter(
            name="promised_date",
            param_type="string",
            description="Date the user promised to pay (ISO 8601).",
            required=True,
        ),
        ToolParameter(
            name="amount",
            param_type="number",
            description="Promised payment amount.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        promised_date = kwargs.get("promised_date", "2025-04-15")
        amount = kwargs.get("amount", 2580.00)
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "promised_date": promised_date,
                "amount": amount,
                "promise_id": f"promise-{user_id}-001",
                "status": "recorded",
            },
        )


class CheckPaymentStatusTool(Tool):
    name = "check_payment_status"
    description = "Verify whether the user has made a payment."
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
                "paid": False,
                "last_payment_date": None,
                "remaining_balance": 2580.00,
            },
        )
