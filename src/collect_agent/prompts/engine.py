"""Prompt engine for dynamic template assembly."""

from pathlib import Path
from typing import Any

from collect_agent.tools.base import Tool


TEMPLATE_DIR = Path(__file__).parent / "templates"


class PromptEngine:
    """Assemble prompts from template fragments."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        self._cache: dict[str, str] = {}

    def load_fragment(self, name: str) -> str:
        """Load a template file by relative path (cached)."""
        if name in self._cache:
            return self._cache[name]
        path = self.template_dir / name
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        self._cache[name] = content
        return content

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()

    def assemble_skill_prompt(self, skill_name: str, context: dict[str, Any]) -> str:
        """Assemble full prompt for a skill execution."""
        parts: list[str] = []

        # 1. Constitutional rules
        constitution = self.load_fragment("constitutional_rules.md")
        if constitution:
            parts.append(f"## 宪法规则\n{constitution}")

        # 2. Skill-specific template
        skill_template = self.load_fragment(f"skills/{skill_name}.xml")
        if not skill_template:
            skill_template = self.load_fragment(f"skills/{skill_name}.md")
        if skill_template:
            parts.append(f"## 任务\n{skill_template}")

        # 3. CoT SOP
        cot = self.load_fragment("cot_sop.md")
        if cot:
            parts.append(f"## 思考流程\n{cot}")

        # 4. XML output schema
        schema = self.load_fragment("skill_base.xml")
        if schema:
            parts.append(f"## 输出格式\n{schema}")

        # 5. Few-shot examples
        intent_cat = context.get("intent_category", "")
        few_shots = self._load_few_shots(intent_cat)
        if few_shots:
            parts.append(f"## 示例\n{few_shots}")

        # 6. Dynamic context
        dynamic = self._build_dynamic_context(context)
        if dynamic:
            parts.append(f"## 当前上下文\n{dynamic}")

        return "\n\n".join(parts)

    def assemble_intent_prompt(self, user_message: str, context: dict[str, Any]) -> str:
        """Assemble prompt for intent recognition."""
        parts: list[str] = []

        constitution = self.load_fragment("constitutional_rules.md")
        if constitution:
            parts.append(f"## 宪法规则\n{constitution}")

        cot = self.load_fragment("cot_sop.md")
        if cot:
            parts.append(f"## 思考流程\n{cot}")

        schema = self.load_fragment("intent_recognition.xml")
        if schema:
            parts.append(f"## 输出格式\n{schema}")

        dynamic = self._build_dynamic_context(context)
        if dynamic:
            parts.append(f"## 当前上下文\n{dynamic}")

        parts.append(f"## 用户消息\n{user_message}")

        return "\n\n".join(parts)

    def get_tool_schemas(self, tools: list[Tool]) -> str:
        """Generate XML tool descriptions for prompt injection."""
        descriptions = [t.to_xml_description() for t in tools]
        return "\n".join(["## 可用工具"] + descriptions)

    def _load_few_shots(self, intent_category: str) -> str:
        """Load few-shot examples for given intent category."""
        mapping = {
            "A": "cooperative_a.md",
            "B": "negotiation_b.md",
            "C": "avoidance_c.md",
            "D": "dispute_d.md",
            "E": "complaint_e.md",
            "STOP": "stop.md",
            "CRISIS": "crisis.md",
        }
        filename = mapping.get(intent_category, "")
        if filename:
            return self.load_fragment(f"few_shots/{filename}")
        return ""

    def _build_dynamic_context(self, context: dict[str, Any]) -> str:
        """Build dynamic context section."""
        lines: list[str] = []

        session_state = context.get("session_state")
        if session_state:
            lines.append(f"会话状态: {session_state}")

        user_profile = context.get("user_profile")
        if user_profile:
            lines.append(f"用户: {getattr(user_profile, 'name', '未知')}")
            lines.append(f"逾期天数: {getattr(user_profile, 'overdue_days', 0)}")
            lines.append(f"逾期金额: {getattr(user_profile, 'amount_due', 0)}")

        bill_facts = context.get("bill_facts", {})
        if bill_facts:
            lines.append("账单信息:")
            for k, v in bill_facts.items():
                lines.append(f"  {k}: {v}")

        history = context.get("conversation_history", [])
        if history:
            lines.append("最近对话:")
            for msg in history[-5:]:
                direction = (
                    "用户" if getattr(msg, "direction", "") == "inbound" else "助手"
                )
                content = getattr(msg, "content", "")
                lines.append(f"  {direction}: {content}")

        tools = context.get("available_tools", [])
        if tools:
            lines.append(self.get_tool_schemas(tools))

        return "\n".join(lines)
