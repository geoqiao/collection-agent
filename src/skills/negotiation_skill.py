"""Negotiation skill for users unwilling or unable to pay."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord
from src.tools.base import ToolResult


class NegotiationSkill(Skill):
    name = "negotiation"
    description = "与债务人协商还款计划或延期"
    triggers = ["B", "UNWILLING_TO_PAY"]
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

        # 2. Parse intent / message to decide: payment plan vs promise
        user_msg = (ctx.user_message or "").lower()

        if "分期" in user_msg or "plan" in user_msg:
            installments = 3
            plan_result = await self._call_tool(
                "create_payment_plan",
                {
                    "user_id": ctx.user_id,
                    "installments": installments,
                    "amount": amount_due,
                },
            )
            actions.append(
                ToolCallRecord(
                    tool_name="create_payment_plan",
                    parameters={
                        "user_id": ctx.user_id,
                        "installments": installments,
                        "amount": amount_due,
                    },
                    result=plan_result,
                )
            )

            per_installment = plan_result.get("per_installment", amount_due / installments)
            message = (
                f"已为您创建分期还款计划：共 {installments} 期，"
                f"每期 {per_installment:.2f} 元。"
                f"首期请于 7 天内支付。"
            )

            # Schedule reminder for first installment
            reminder_result = await self._call_tool(
                "schedule_reminder",
                {
                    "user_id": ctx.user_id,
                    "remind_date": "7_days_later",
                    "channel": "sms",
                    "message": f"提醒：您的分期还款首期 {per_installment:.2f} 元即将到期。",
                },
            )
            actions.append(
                ToolCallRecord(
                    tool_name="schedule_reminder",
                    parameters={
                        "user_id": ctx.user_id,
                        "remind_date": "7_days_later",
                        "channel": "sms",
                        "message": f"提醒：您的分期还款首期 {per_installment:.2f} 元即将到期。",
                    },
                    result=reminder_result,
                )
            )

            return SkillResult(
                status=SkillResultStatus.SUCCESS,
                response_text=message,
                actions=actions,
            )

        # Default: record a promise and schedule reminder
        promised_date = "7_days_later"
        promise_result = await self._call_tool(
            "record_promise",
            {
                "user_id": ctx.user_id,
                "promised_date": promised_date,
                "amount": amount_due,
            },
        )
        actions.append(
            ToolCallRecord(
                tool_name="record_promise",
                parameters={
                    "user_id": ctx.user_id,
                    "promised_date": promised_date,
                    "amount": amount_due,
                },
                result=promise_result,
            )
        )

        reminder_result = await self._call_tool(
            "schedule_reminder",
            {
                "user_id": ctx.user_id,
                "remind_date": promised_date,
                "channel": "sms",
                "message": f"提醒：您承诺于 {promised_date} 还款 {amount_due} 元，请按时处理。",
            },
        )
        actions.append(
            ToolCallRecord(
                tool_name="schedule_reminder",
                parameters={
                    "user_id": ctx.user_id,
                    "remind_date": promised_date,
                    "channel": "sms",
                    "message": f"提醒：您承诺于 {promised_date} 还款 {amount_due} 元，请按时处理。",
                },
                result=reminder_result,
            )
        )

        message = (
            f"理解您的处境。已记录您的还款承诺：{amount_due} 元，"
            f"请于 {promised_date} 前处理。我们会在到期前提醒您。"
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
