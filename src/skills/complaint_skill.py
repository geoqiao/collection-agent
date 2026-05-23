"""Complaint handling skill for handling complaints and threats."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord


class ComplaintSkill(Skill):
    name = "complaint_handling"
    description = "Handle user complaints and threats"
    triggers = ["E", "COMPLAINT"]
    is_one_way_door = True

    async def execute(self, ctx: SkillContext) -> SkillResult:
        actions = []

        pause_tool = next((t for t in self.tools if t.name == "pause_collection"), None)
        if pause_tool:
            result = await pause_tool.execute(
                user_id=ctx.user_id,
                days=2,
                reason="complaint_received",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="pause_collection",
                    parameters={"user_id": ctx.user_id, "days": 2, "reason": "complaint_received"},
                    result=result,
                )
            )

        escalate_tool = next((t for t in self.tools if t.name == "escalate_to_human"), None)
        if escalate_tool:
            result = await escalate_tool.execute(
                user_id=ctx.user_id,
                reason="user_complaint",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="escalate_to_human",
                    parameters={"user_id": ctx.user_id, "reason": "user_complaint"},
                    result=result,
                )
            )

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="非常抱歉我们的服务让您不满。您的投诉已收到，我们将暂停催收2天，并立即安排专员处理您的反馈。专员会在24小时内与您联系，请保持电话畅通。",
            actions=actions,
            new_session_state="escalated",
        )
