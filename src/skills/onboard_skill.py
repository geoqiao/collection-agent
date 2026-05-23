"""Onboard skill for first contact with debtors."""

from __future__ import annotations

from src.skills.base import Skill


class OnboardSkill(Skill):
    name = "onboard"
    description = "首次联系债务人，建立沟通渠道，说明来意并引导后续处理"
    triggers = ["SCHEDULED_OUTREACH", "USER_LOGIN", "REMINDER_DUE"]
    is_one_way_door = False
    prompt_template = "onboard.xml"
