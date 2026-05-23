"""Follow-up skill for checking on payment promises."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord
from src.tools.base import ToolResult


class FollowUpSkill(Skill):
    name = "followup"
    description = "跟进用户还款承诺，提醒未付款项"
    triggers = ["SILENCE_TIMEOUT", "REMINDER_DUE"]
    is_one_way_door = False

    def __init__(self, tools: list | None = None):
        super().__init__(tools)

    async def execute(self, ctx: SkillContext) -> SkillResult:
        actions: list[ToolCallRecord] = []

        # 1. Check payment status
        status_result = await self._call_tool(
            "check_payment_status", {"user_id": ctx.user_id}
        )
        actions.append(
            ToolCallRecord(
                tool_name="check_payment_status",
                parameters={"user_id": ctx.user_id},
                result=status_result,
            )
        )

        paid = status_result.get("paid", False)

        if paid:
            remaining = status_result.get("remaining_balance", 0)
            if remaining == 0:
                message = "感谢您的还款，您的账单已全部结清。如有其他问题请随时联系。"
            else:
                message = f"感谢您的部分还款，剩余欠款 {remaining} 元，请继续按时处理。"
            return SkillResult(
                status=SkillResultStatus.SUCCESS,
                response_text=message,
                actions=actions,
            )

        # 2. If unpaid, query bill and send reminder
        bill_result = await self._call_tool("query_bill", {"user_id": ctx.user_id})
        actions.append(
            ToolCallRecord(
                tool_name="query_bill",
                parameters={"user_id": ctx.user_id},
                result=bill_result,
            )
        )

        amount_due = bill_result.get("amount_due", 0)
        overdue_days = bill_result.get("overdue_days", 0)

        message = (
            f"提醒：您的账单尚有 {amount_due} 元未还，"
            f"已逾期 {overdue_days} 天。"
            f"请尽快处理，以免影响您的信用记录。"
        )

        send_result = await self._call_tool(
            "send_message",
            {"user_id": ctx.user_id, "channel": "sms", "message": message},
        )
        actions.append(
            ToolCallRecord(
                tool_name="send_message",
                parameters={
                    "user_id": ctx.user_id,
                    "channel": "sms",
                    "message": message,
                },
                result=send_result,
            )
        )

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text=message,
            actions=actions,
        )

    async def _call_tool(self, tool_name: str, parameters: dict) -> dict:
        for tool in self.tools:
            if tool.name == tool_name:
                result = await tool.execute(**parameters)
                return {"success": result.success, **result.data}
        return {"success": False, "error": f"Tool {tool_name} not found"}
