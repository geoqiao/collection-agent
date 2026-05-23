"""Stop handling skill for honoring stop requests."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord


class StopSkill(Skill):
    name = "stop_handling"
    description = "Honor user stop requests and add to DNC list"
    triggers = ["STOP"]
    is_one_way_door = True
    prompt_template = "stop.xml"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        """Execute stop handling: add to DNC list and pause collection."""
        actions: list[ToolCallRecord] = []
        from src.tools.compliance import PauseCollectionTool
        from src.tools.user import AddToDncListTool

        required_tools = [AddToDncListTool, PauseCollectionTool]
        for tool_cls in required_tools:
            tool = tool_cls()
            if isinstance(tool, AddToDncListTool):
                result = await tool.execute(user_id=ctx.user_id, channel="all")
                params = {"user_id": ctx.user_id, "channel": "all"}
            else:
                result = await tool.execute(user_id=ctx.user_id, reason="user stop request", days=365)
                params = {"user_id": ctx.user_id, "reason": "user stop request", "days": 365}
            actions.append(ToolCallRecord(
                tool_name=tool.name,
                parameters=params,
                result=result.data if result.success else {"error": result.error},
            ))

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="已收到您的要求。我已立即停止所有联系，并将您加入免打扰名单。",
            actions=actions,
            new_session_state="stopped",
            escalation=False,
            thinking="Stop request received: added to DNC list and paused collection.",
        )
