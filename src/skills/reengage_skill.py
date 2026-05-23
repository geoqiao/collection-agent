"""Re-engage skill for re-establishing contact."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord
from src.tools.base import ToolResult


class ReEngageSkill(Skill):
    name = "reengage"
    description = "当联系无效时，通过替代渠道重新建立联系"
    triggers = ["INEFFECTIVE_CONTACT", "CALL_NO_ANSWER", "SILENCE_TIMEOUT"]
    is_one_way_door = False

    def __init__(self, tools: list | None = None):
        super().__init__(tools)

    async def execute(self, ctx: SkillContext) -> SkillResult:
        actions: list[ToolCallRecord] = []

        # 1. Query user history to find last contact channel
        history_result = await self._call_tool(
            "query_user_history", {"user_id": ctx.user_id}
        )
        actions.append(
            ToolCallRecord(
                tool_name="query_user_history",
                parameters={"user_id": ctx.user_id},
                result=history_result,
            )
        )

        # 2. Pick alternative channel
        last_channel = history_result.get("last_channel", "sms")
        channel_map = {
            "sms": "email",
            "email": "whatsapp",
            "whatsapp": "sms",
            "call": "sms",
        }
        alt_channel = channel_map.get(last_channel, "email")

        message = (
            "您好，我们多次尝试联系您未果。"
            "请留意您的账单情况，如有疑问请随时回复。"
        )

        send_result = await self._call_tool(
            "send_message",
            {"user_id": ctx.user_id, "channel": alt_channel, "message": message},
        )
        actions.append(
            ToolCallRecord(
                tool_name="send_message",
                parameters={
                    "user_id": ctx.user_id,
                    "channel": alt_channel,
                    "message": message,
                },
                result=send_result,
            )
        )

        # 3. Schedule follow-up reminder
        reminder_result = await self._call_tool(
            "schedule_reminder",
            {
                "user_id": ctx.user_id,
                "remind_date": "3_days_later",
                "channel": alt_channel,
                "message": "再次提醒：请尽快处理您的账单欠款。",
            },
        )
        actions.append(
            ToolCallRecord(
                tool_name="schedule_reminder",
                parameters={
                    "user_id": ctx.user_id,
                    "remind_date": "3_days_later",
                    "channel": alt_channel,
                    "message": "再次提醒：请尽快处理您的账单欠款。",
                },
                result=reminder_result,
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
