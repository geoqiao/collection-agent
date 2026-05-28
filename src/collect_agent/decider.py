"""Decider — single LLM call for intent recognition + skill selection.

The LLM receives multi-signal context and outputs:
    intent + selected_skill + confidence + escalation + emotion + reasoning
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from collect_agent.core.context import Context
from collect_agent.intent.models import IntentCategory
from collect_agent.llm.base import LLMClient
from collect_agent.skills.registry import SkillRegistry


@dataclass
class Decision:
    """Output of the Decide phase."""

    intent: IntentCategory
    selected_skill: str
    confidence: str = "medium"
    escalation: bool = False
    emotion: str = "neutral"
    reasoning: str = ""


_SYSTEM_PROMPT_TEMPLATE = """你是专业的债务催收意图识别助手。

你的任务不是"分类用户文本"，而是根据**所有可用信号**推断用户当前状态，并选择最合适的 Skill 来应对。

# 宪法规则（绝对不可违反）
1. 禁止任何威胁、恐吓或羞辱性语言
2. 禁止编造或猜测金额、日期、逾期天数 — 必须仅从 <facts> 读取
3. STOP / 投诉 / 危机 / 争议触发后，立即停止催收话术
4. 每轮必须重新评估用户意图
5. 回复语气必须在"温和提醒"范围内

# 意图路由表
- COOPERATION：愿意还款或询问还款方式 → 引导还款
- NEGOTIATION：表示困难，希望延期或分期 → 共情，提供方案
- AVOIDANCE：回避问题，不愿深入讨论 → 简短确认，不持续施压
- DISPUTE：质疑账单真实性或金额 → 道歉，移交人工
- COMPLAINT：表达不满，威胁投诉 → 暂停，安抚，移交
- STOP：明确要求停止联系 → 确认退出
- CRISIS：提及自杀、重病等 → 安慰，立即人工告警

# 可选 Skills
{{skills_description}}

# 思考流程（每轮必须执行）
1. 当前 session_state 是什么？如果是 locked 状态（escalated/stopped/crisis/disputed），立即使用固定模板
2. 读取最近 3 轮对话。用户情绪是否显著转变？
3. 本轮核心意图是什么？基于所有信号综合判断，不是只看文本
4. 该意图是否触发单向门（DISPUTE/COMPLAINT/STOP/CRISIS）？
5. 如需回复，回复中的金额和日期是否与 <facts> 完全匹配？
6. 回复语气是否在"温和提醒"范围内？
7. 选择哪个 skill 最合适？从可选 skills 中选择

# 输出格式（JSON）
你必须以 JSON 格式输出。提示词中必须包含 "json" 字样以确保格式正确。

输出字段：
- intent: COOPERATION|NEGOTIATION|AVOIDANCE|DISPUTE|COMPLAINT|STOP|CRISIS
- selected_skill: 从可选 Skills 中选择的 skill 名称
- confidence: high|medium|low
- escalation: true|false
- emotion: positive|neutral|negative|angry
- thinking: 你的推理过程（必须引用具体信号）

示例：
{
  "intent": "NEGOTIATION",
  "selected_skill": "negotiation",
  "confidence": "high",
  "escalation": false,
  "emotion": "negative",
  "thinking": "用户明确表示'手头紧'和'延期'，历史记录显示此前承诺还款但未履行，属于协商意图。"
}
"""


class Decider:
    """Decide intent and skill in a single LLM call."""

    def __init__(
        self,
        llm_client: LLMClient,
        skill_registry: SkillRegistry,
    ) -> None:
        self._llm = llm_client
        self._skills = skill_registry

    def _build_system_prompt(self) -> str:
        """Build system prompt with current skills list."""
        skill_lines = []
        for skill in self._skills.list_skills():
            skill_lines.append(f"- {skill.name}: {skill.description}")

        skills_desc = "\n".join(skill_lines) if skill_lines else "（无）"

        return _SYSTEM_PROMPT_TEMPLATE.replace(
            "{{skills_description}}",
            skills_desc,
        )

    async def decide(self, context: Context) -> Decision:
        """Run the decide phase."""
        system_prompt = self._build_system_prompt()
        user_prompt = context.to_prompt()

        response = await self._llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=2048,
        )

        raw = response.content if hasattr(response, "content") else str(response)
        return self._parse(raw)

    def _parse(self, raw: str) -> Decision:
        """Parse JSON response from LLM."""
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from surrounding text
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                try:
                    parsed = json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    parsed = {}
            else:
                parsed = {}

        intent_str = parsed.get("intent", "UNKNOWN").upper()
        skill_name = parsed.get("selected_skill", "")

        # Fallback intent mapping
        intent = _map_intent(intent_str)

        # Fallback skill
        if not skill_name or not self._skills.get(skill_name):
            skill_name = _fallback_skill(intent)

        return Decision(
            intent=intent,
            selected_skill=skill_name,
            confidence=parsed.get("confidence", "medium").lower(),
            escalation=bool(parsed.get("escalation", False)),
            emotion=parsed.get("emotion", "neutral").lower(),
            reasoning=parsed.get("thinking", ""),
        )


def _map_intent(val: str) -> IntentCategory:
    mapping = {
        "A": IntentCategory.COOPERATION,
        "B": IntentCategory.NEGOTIATION,
        "C": IntentCategory.AVOIDANCE,
        "D": IntentCategory.DISPUTE,
        "E": IntentCategory.COMPLAINT,
        "COOPERATION": IntentCategory.COOPERATION,
        "NEGOTIATION": IntentCategory.NEGOTIATION,
        "AVOIDANCE": IntentCategory.AVOIDANCE,
        "DISPUTE": IntentCategory.DISPUTE,
        "COMPLAINT": IntentCategory.COMPLAINT,
        "STOP": IntentCategory.STOP,
        "CRISIS": IntentCategory.CRISIS,
    }
    return mapping.get(val, IntentCategory.UNKNOWN)


def _fallback_skill(intent: IntentCategory) -> str:
    mapping = {
        IntentCategory.COOPERATION: "payment_guidance",
        IntentCategory.NEGOTIATION: "negotiation",
        IntentCategory.AVOIDANCE: "reengage",
        IntentCategory.DISPUTE: "dispute",
        IntentCategory.COMPLAINT: "complaint",
        IntentCategory.STOP: "stop",
        IntentCategory.CRISIS: "crisis",
    }
    return mapping.get(intent, "troubleshoot")
