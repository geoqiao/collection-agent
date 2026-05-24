"""Complaint handling skill for handling complaints and threats."""

from __future__ import annotations

from collect_agent.skills.base import Skill


class ComplaintSkill(Skill):
    name = "complaint_handling"
    description = "Handle user complaints and threats with immediate de-escalation"
    triggers = ["E", "COMPLAINT"]
    is_one_way_door = True
    prompt_template = "complaint.xml"
