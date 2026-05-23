"""Onboard skill for first contact with debtors."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord
from src.tools.base import ToolResult


class OnboardSkill(Skill):
    name = "onboard"
    description = "首次联系债务人，查询账单并发送初始 outreach 消息"
    triggers = ["SCHEDULED_OUTREACH", "USER_LOGIN", "REMINDER_DUE"]
    is_one_way_door = False

    def __init__(self, tools: list | None = None):
        super().__init__(tools)

    async def execute(self, ctx: SkillContext) -> SkillResult:
        actions: list[ToolCallRecord] = []

        # 1. Query bill
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
        due_date = bill_result.get("due_date", "")

        # 2. Query user history
        history_result = await self._call_tool("query_user_history", {"user_id": ctx.user_id})
        actions.append(
            ToolCallRecord(
                tool_name="query_user_history",
                parameters={"user_id": ctx.user_id},
                result=history_result,
            )
        )

        # 3. Select channel and send personalized message
        channel = "sms"
        if ctx.user_profile and getattr(ctx.user_profile, "preferred_channel", None):
            channel = ctx.user_profile.preferred_channel

        message = (
            f"您好，您的账单尚有欠款 {amount_due} 元，"
            f"已逾期 {overdue_days} 天（应还日期：{due_date}）。"
            f"请及时处理，如有疑问请回复。"
        )

        send_result = await self._call_tool(
            "send_message",
            {"user_id": ctx.user_id, "channel": channel, "message": message},
        )
        actions.append(
            ToolCallRecord(
                tool_name="send_message",
                parameters={
                    "user_id": ctx.user_id,
                    "channel": channel,
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
