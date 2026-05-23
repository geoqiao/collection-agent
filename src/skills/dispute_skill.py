"""Dispute resolution skill for handling bill disputes."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord


class DisputeSkill(Skill):
    name = "dispute_resolution"
    description = "Handle bill disputes raised by users"
    triggers = ["D", "DISPUTE"]
    is_one_way_door = True

    async def execute(self, ctx: SkillContext) -> SkillResult:
        actions = []

        pause_tool = next((t for t in self.tools if t.name == "pause_collection"), None)
        if pause_tool:
            result = await pause_tool.execute(
                user_id=ctx.user_id,
                days=7,
                reason="user_dispute",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="pause_collection",
                    parameters={"user_id": ctx.user_id, "days": 7, "reason": "user_dispute"},
                    result=result,
                )
            )

        escalate_tool = next((t for t in self.tools if t.name == "escalate_to_human"), None)
        if escalate_tool:
            result = await escalate_tool.execute(
                user_id=ctx.user_id,
                reason="dispute_raised",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="escalate_to_human",
                    parameters={"user_id": ctx.user_id, "reason": "dispute_raised"},
                    result=result,
                )
            )

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="非常抱歉给您带来困扰。您的账单争议已记录，我们将暂停催收7天，并安排专人核实账单详情。通常调查需要3-5个工作日，结果将通过短信或邮件通知您。",
            actions=actions,
            new_session_state="disputed",
        )
