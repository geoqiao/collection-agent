"""Re-engage skill for re-establishing contact."""

from __future__ import annotations

from src.skills.base import Skill


class ReEngageSkill(Skill):
    name = "reengage"
    description = "当联系无效时，通过替代渠道重新建立联系"
    triggers = ["INEFFECTIVE_CONTACT", "CALL_NO_ANSWER", "SILENCE_TIMEOUT"]
    is_one_way_door = False
    prompt_template = "reengage.xml"
