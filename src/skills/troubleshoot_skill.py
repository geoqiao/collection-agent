"""Troubleshoot skill for technical/operation inquiries."""

from __future__ import annotations

from src.skills.base import Skill


class TroubleshootSkill(Skill):
    name = "troubleshoot"
    description = "帮助用户解决技术问题或操作疑问"
    triggers = ["OPERATION_INQUIRY"]
    is_one_way_door = False
    prompt_template = "troubleshoot.xml"
