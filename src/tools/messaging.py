"""Messaging-related tools."""

from __future__ import annotations

from typing import Any

from src.tools.base import Tool, ToolParameter, ToolResult


class SendMessageTool(Tool):
    name = "send_message"
    description = "Send a message to the user via a specified channel (e.g., sms, email, whatsapp)."
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
            description="Channel to send the message through.",
            required=True,
            enum=["sms", "email", "whatsapp"],
        ),
        ToolParameter(
            name="message",
            param_type="string",
            description="Message content to send.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        channel = kwargs.get("channel", "sms")
        message = kwargs.get("message", "")
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "channel": channel,
                "message_preview": message[:50],
                "status": "sent",
                "timestamp": "2025-04-12T10:00:00Z",
            },
        )


class SendPaymentLinkTool(Tool):
    name = "send_payment_link"
    description = "Generate and send a payment URL to the user."
    parameters = [
        ToolParameter(
            name="user_id",
            param_type="string",
            description="Unique identifier for the user.",
            required=True,
        ),
        ToolParameter(
            name="amount",
            param_type="number",
            description="Amount to be paid.",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, error = self._validate_params(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)
        user_id = kwargs.get("user_id", "unknown")
        amount = kwargs.get("amount", 2580.00)
        return ToolResult(
            success=True,
            data={
                "user_id": user_id,
                "amount": amount,
                "payment_url": f"https://pay.example.com/u/{user_id}?amount={amount}",
                "expires_at": "2025-04-15T23:59:59Z",
            },
        )
