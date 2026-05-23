"""Complaint handling skill for handling complaints and threats."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord


class ComplaintSkill(Skill):
    name = "complaint_handling"
    description = "Handle user complaints and threats with immediate de-escalation"
    triggers = ["E", "COMPLAINT"]
    is_one_way_door = True
    prompt_template = "complaint.xml"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        """Execute complaint handling: pause collection and escalate to human."""
        actions: list[ToolCallRecord] = []
        from src.tools.compliance import PauseCollectionTool, EscalateToHumanTool

        for tool_cls in (PauseCollectionTool, EscalateToHumanTool):
            tool = tool_cls()
            result = await tool.execute(user_id=ctx.user_id, reason="user complaint")
            actions.append(ToolCallRecord(
                tool_name=tool.name,
                parameters={"user_id": ctx.user_id, "reason": "user complaint"},
                result=result.data if result.success else {"error": result.error},
            ))

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="非常抱歉给您带来了不好的体验。您的投诉我已记录并升级至专人处理，后续将由投诉专员与您联系。",
            actions=actions,
            new_session_state="escalated",
            escalation=True,
            thinking="Complaint received: paused collection and escalated to human.",
        )
