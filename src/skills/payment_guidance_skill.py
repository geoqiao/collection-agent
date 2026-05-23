"""Payment guidance skill for users willing to pay."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord
from src.tools.base import ToolResult


class PaymentGuidanceSkill(Skill):
    name = "payment_guidance"
    description = "引导用户完成还款，发送支付链接或解释支付方式"
    triggers = ["A", "WILLING_TO_PAY", "PAYMENT_METHOD_INQUIRY"]
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

        # 2. Decide action based on intent
        if ctx.current_intent == "PAYMENT_METHOD_INQUIRY":
            message = (
                "您可以通过以下方式还款：\n"
                "1. 银行转账\n"
                "2. 支付宝/微信支付\n"
                "3. 点击支付链接直接付款\n"
                "如需支付链接，请回复“链接”。"
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

        # Default: send payment link
        link_result = await self._call_tool(
            "send_payment_link",
            {"user_id": ctx.user_id, "amount": amount_due},
        )
        actions.append(
            ToolCallRecord(
                tool_name="send_payment_link",
                parameters={"user_id": ctx.user_id, "amount": amount_due},
                result=link_result,
            )
        )

        payment_url = link_result.get("payment_url", "")
        message = (
            f"感谢您的配合！您的账单金额为 {amount_due} 元。"
            f"请点击以下链接完成支付：{payment_url}"
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
