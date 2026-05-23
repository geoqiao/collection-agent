"""Follow-up skill for checking on payment promises."""

from __future__ import annotations

from src.skills.base import Skill


class FollowUpSkill(Skill):
    name = "followup"
    description = "跟进用户还款承诺，提醒未付款项"
    triggers = ["SILENCE_TIMEOUT", "REMINDER_DUE"]
    is_one_way_door = False
    prompt_template = "followup.xml"
