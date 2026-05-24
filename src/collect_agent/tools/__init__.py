"""Tools package — exports all tools and the registry."""

from __future__ import annotations

from collect_agent.tools.base import Tool, ToolParameter, ToolResult
from collect_agent.tools.billing import CreatePaymentPlanTool, QueryBillTool
from collect_agent.tools.compliance import EscalateToHumanTool, PauseCollectionTool, WelfareAlertTool
from collect_agent.tools.messaging import SendMessageTool, SendPaymentLinkTool
from collect_agent.tools.promises import CheckPaymentStatusTool, RecordPromiseTool
from collect_agent.tools.registry import ToolRegistry
from collect_agent.tools.user import AddToDncListTool, QueryUserHistoryTool, ScheduleReminderTool

__all__ = [
    "Tool",
    "ToolParameter",
    "ToolResult",
    "ToolRegistry",
    "QueryBillTool",
    "CreatePaymentPlanTool",
    "SendMessageTool",
    "SendPaymentLinkTool",
    "RecordPromiseTool",
    "CheckPaymentStatusTool",
    "PauseCollectionTool",
    "EscalateToHumanTool",
    "WelfareAlertTool",
    "QueryUserHistoryTool",
    "AddToDncListTool",
    "ScheduleReminderTool",
]
