"""Crisis intervention skill for handling crisis signals."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord


class CrisisSkill(Skill):
    name = "crisis_intervention"
    description = "Handle crisis signals from users"
    triggers = ["CRISIS"]
    is_one_way_door = True

    async def execute(self, ctx: SkillContext) -> SkillResult:
        actions = []

        pause_tool = next((t for t in self.tools if t.name == "pause_collection"), None)
        if pause_tool:
            result = await pause_tool.execute(
                user_id=ctx.user_id,
                days=7,
                reason="crisis_signal",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="pause_collection",
                    parameters={"user_id": ctx.user_id, "days": 7, "reason": "crisis_signal"},
                    result=result,
                )
            )

        welfare_tool = next((t for t in self.tools if t.name == "welfare_alert"), None)
        if welfare_tool:
            result = await welfare_tool.execute(
                user_id=ctx.user_id,
                details="Crisis signal detected",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="welfare_alert",
                    parameters={"user_id": ctx.user_id, "details": "Crisis signal detected"},
                    result=result,
                )
            )

        escalate_tool = next((t for t in self.tools if t.name == "escalate_to_human"), None)
        if escalate_tool:
            result = await escalate_tool.execute(
                user_id=ctx.user_id,
                reason="crisis_intervention",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="escalate_to_human",
                    parameters={"user_id": ctx.user_id, "reason": "crisis_intervention"},
                    result=result,
                )
            )

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="我们非常关心您的情况。催收已暂停，相关团队已收到提醒。如果您感到情绪低落或需要帮助，请拨打全国24小时心理援助热线：400-161-9995，或联系当地危机干预中心。您并不孤单，有人愿意帮助您。",
            actions=actions,
            new_session_state="crisis",
        )
