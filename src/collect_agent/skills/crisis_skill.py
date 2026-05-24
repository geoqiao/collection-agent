"""Crisis intervention skill for handling crisis signals."""

from __future__ import annotations

from collect_agent.skills.base import Skill


class CrisisSkill(Skill):
    name = "crisis_intervention"
    description = (
        "Handle crisis signals from users with immediate safety-first response"
    )
    triggers = ["CRISIS"]
    is_one_way_door = True
    prompt_template = "crisis.xml"
