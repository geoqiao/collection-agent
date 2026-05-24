from collect_agent.core.constants import Intent
from collect_agent.core.models import UserProfile
from collect_agent.strategy.strategies import RESPONSE_TEMPLATES, STRATEGIES


class StrategyEngine:
    def select_strategy(self, user: UserProfile, intent: Intent) -> dict:
        if user.is_sensitive:
            return STRATEGIES["standard_reminder"]
        return STRATEGIES.get(intent, STRATEGIES[Intent.INEFFECTIVE_CONTACT])

    def get_response(self, user: UserProfile, strategy: dict, context: dict) -> str:
        strategy_type = strategy.get("type", "unknown")
        templates = RESPONSE_TEMPLATES.get(strategy_type, ["请尽快处理您的逾期账单。"])

        if not templates:
            return "请尽快处理您的逾期账单。"

        round_num = context.get("round", 0)
        template = (
            templates[round_num]
            if round_num < len(templates)
            else templates[-1]
        )

        return template.format(
            name=user.name or "用户",
            amount=user.amount_due,
            days=user.overdue_days,
            date=context.get("planned_date", ""),
        )
