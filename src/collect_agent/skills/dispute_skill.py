"""Dispute resolution skill for handling bill disputes."""

from __future__ import annotations

from collect_agent.skills.base import Skill


class DisputeSkill(Skill):
    name = "dispute_resolution"
    description = "Handle bill disputes raised by users with immediate pause and escalation"
    triggers = ["D", "DISPUTE"]
    is_one_way_door = True
    prompt_template = "dispute.xml"
