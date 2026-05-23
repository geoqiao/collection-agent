"""Dispute resolution skill for handling bill disputes."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord


class DisputeSkill(Skill):
    name = "dispute_resolution"
    description = "Handle bill disputes raised by users with immediate pause and escalation"
    triggers = ["D", "DISPUTE"]
    is_one_way_door = True
    prompt_template = "dispute.xml"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        """Execute dispute handling: pause collection and escalate to human."""
        actions: list[ToolCallRecord] = []
        from src.tools.compliance import PauseCollectionTool, EscalateToHumanTool

        for tool_cls in (PauseCollectionTool, EscalateToHumanTool):
            tool = tool_cls()
            result = await tool.execute(user_id=ctx.user_id, reason="user dispute")
            actions.append(ToolCallRecord(
                tool_name=tool.name,
                parameters={"user_id": ctx.user_id, "reason": "user dispute"},
                result=result.data if result.success else {"error": result.error},
            ))

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="您的争议我已记录。在争议调查期间，我们将暂停催收联系。调查完成后我们会第一时间通知您。",
            actions=actions,
            new_session_state="disputed",
            escalation=True,
            thinking="Dispute received: paused collection and escalated to human.",
        )
