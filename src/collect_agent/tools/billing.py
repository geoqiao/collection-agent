"""Billing-related tools."""

from __future__ import annotations

from typing import Any

from collect_agent.tools.base import Tool, ToolParameter, ToolResult


class QueryBillTool(Tool):
    name = "query_bill"
    description = "Query the user's current bill details including amount due, overdue days, and due date."
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
                "amount_due": 2580.00,
                "overdue_days": 3,
                "due_date": "2025-04-15",
                "currency": "USD",
            },
        )


class CreatePaymentPlanTool(Tool):
    name = "create_payment_plan"
    description = "Propose an installment payment plan for the user."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
        ToolParameter(
            name="installments",
            param_type="number",
            description="Number of installments.",
            required=True,
        ),
        ToolParameter(
            name="amount",
            param_type="number",
            description="Total amount to be paid.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        installments = int(kwargs.get("installments", 3))
        amount = float(kwargs.get("amount", 2580.00))
        per_installment = round(amount / installments, 2)
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "installments": installments,
                "amount": amount,
                "per_installment": per_installment,
                "status": "proposed",
            },
        )
