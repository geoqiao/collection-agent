"""Negotiation skill for users unwilling or unable to pay."""

from __future__ import annotations

from src.skills.base import Skill


class NegotiationSkill(Skill):
    name = "negotiation"
    description = "与债务人协商还款计划或延期"
    triggers = ["B", "UNWILLING_TO_PAY"]
    is_one_way_door = False
    prompt_template = "negotiation.xml"
