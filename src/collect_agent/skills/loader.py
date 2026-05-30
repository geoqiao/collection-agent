"""Skill loader — parses Markdown + YAML frontmatter.

Skills are declarative configuration, not Python classes.
Inspired by pi's SKILL.md standard.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from collect_agent.skills.base import Skill

# Match YAML frontmatter between --- delimiters
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


class SkillLoader:
    """Load skills from Markdown files."""

    def __init__(self, skills_dir: Path | None = None) -> None:
        if skills_dir is None:
            skills_dir = Path(__file__).parents[1] / "prompts" / "templates" / "skills"
        self._dir = skills_dir

    def load_all(self) -> list[Skill]:
        """Load all .md files in the skills directory."""
        skills: list[Skill] = []
        if not self._dir.exists():
            return skills

        for path in sorted(self._dir.glob("*.md")):
            skill = self.load_one(path)
            if skill:
                skills.append(skill)

        return skills

    def load_one(self, path: Path) -> Skill | None:
        """Load a single skill from a Markdown file."""
        content = path.read_text(encoding="utf-8")
        return self._parse(content)

    def _parse(self, raw: str) -> Skill | None:
        """Parse frontmatter + body from raw markdown."""
        m = _FRONTMATTER_RE.match(raw.strip())
        if not m:
            # No frontmatter — try to infer from heading
            return self._parse_legacy(raw)

        frontmatter_raw, body = m.groups()
        try:
            meta: dict[str, Any] = yaml.safe_load(frontmatter_raw) or {}
        except yaml.YAMLError:
            return None

        name = meta.get("name", "")
        description = meta.get("description", "")
        tools = meta.get("tools", [])
        max_steps = meta.get("max_steps", 1000)

        if not name or not description:
            return None

        return Skill(
            name=name,
            description=description,
            tools=tools if isinstance(tools, list) else [],
            max_steps=max_steps,
            content=body.strip(),
        )

    def _parse_legacy(self, raw: str) -> Skill | None:
        """Fallback: try to parse a markdown file without frontmatter."""
        # Look for # heading as name
        name_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
        if not name_match:
            return None

        name = name_match.group(1).strip().lower().replace(" ", "_")
        # Use first paragraph as description
        desc_match = re.search(r"\n\n([^#\n].+?)\n", raw)
        description = desc_match.group(1).strip() if desc_match else name

        return Skill(
            name=name,
            description=description,
            content=raw.strip(),
        )
