"""Payment guidance skill for users willing to pay."""

from __future__ import annotations

from collect_agent.skills.base import Skill


class PaymentGuidanceSkill(Skill):
    name = "payment_guidance"
    description = "引导用户完成还款，发送支付链接或解释支付方式"
    triggers = ["A", "WILLING_TO_PAY", "PAYMENT_METHOD_INQUIRY"]
    is_one_way_door = False
    prompt_template = "payment_guidance.xml"
