"""Stop handling skill for honoring stop requests."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord


class StopSkill(Skill):
    name = "stop_handling"
    description = "Honor user stop requests and add to DNC list"
    triggers = ["STOP"]
    is_one_way_door = True

    async def execute(self, ctx: SkillContext) -> SkillResult:
        actions = []

        dnc_tool = next((t for t in self.tools if t.name == "add_to_dnc_list"), None)
        if dnc_tool:
            result = await dnc_tool.execute(
                user_id=ctx.user_id,
                channel="all",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="add_to_dnc_list",
                    parameters={"user_id": ctx.user_id, "channel": "all"},
                    result=result,
                )
            )

        pause_tool = next((t for t in self.tools if t.name == "pause_collection"), None)
        if pause_tool:
            result = await pause_tool.execute(
                user_id=ctx.user_id,
                days=999999,
                reason="user_stop_request",
            )
            actions.append(
                ToolCallRecord(
                    tool_name="pause_collection",
                    parameters={"user_id": ctx.user_id, "days": 999999, "reason": "user_stop_request"},
                    result=result,
                )
            )

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text="已收到您的停止请求。我们将立即停止所有催收联系，并将您加入勿扰名单。如有账单问题，您仍可通过官方客服热线或官网自助查询。感谢您的理解。",
            actions=actions,
            new_session_state="stopped",
        )
