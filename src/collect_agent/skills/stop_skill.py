"""Stop handling skill for honoring stop requests."""

from __future__ import annotations

from collect_agent.skills.base import Skill


class StopSkill(Skill):
    name = "stop_handling"
    description = "Honor user stop requests and add to DNC list"
    triggers = ["STOP"]
    is_one_way_door = True
    prompt_template = "stop.xml"
