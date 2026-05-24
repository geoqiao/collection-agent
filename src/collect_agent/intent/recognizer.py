"""LLM-based intent recognizer with guardrails."""

import re
from typing import Any

from collect_agent.intent.models import (
    ConfidenceLevel,
    EmotionLevel,
    IntentCategory,
    IntentResult,
)
from collect_agent.session.enhanced_state_machine import ONE_WAY_DOOR_STATES

COOPERATION_KEYWORDS = ["我会还", "愿意还", "马上还", "尽快还", "会处理", "会支付", "愿意还款", "会还款"]
STOP_KEYWORDS = ["停止", "退订", "取消", "不要再打"]
CRISIS_KEYWORDS = ["自杀", "不想活了", "重病", "活不下去"]

_SYSTEM_PROMPT = """你是专业的债务催收意图识别助手。请根据用户消息和会话上下文，严格按以下步骤推理并输出结果。

## 意图路由表
A — 合作：愿意还款或询问还款方式
B — 协商：表示困难，希望延期或分期
C — 回避：回避问题，不愿深入讨论
D — 争议：质疑账单真实性或金额
E — 投诉/威胁：表达不满，威胁投诉
STOP — 停止联系（用户明确要求停止催收）
CRISIS — 危机信号

## 重要区分
- 用户说"我会还的""愿意还款""马上处理"属于 A（合作），不是 STOP
- STOP 仅限于用户明确要求"停止联系""不要再打""退订"等

## 示例
用户消息："我会还的"
<intent>
  <category>A</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>positive</emotion>
</intent>
<thinking>用户明确表示还款意愿，属于合作意图。</thinking>

## CoT SOP
1. 当前会话状态是什么？
2. 最近3轮对话？
3. 用户情绪？
4. 本轮核心意图？
5. 是否触发单向门？
6. 置信度？

## 输出格式（XML）
<intent>
  <category>A|B|C|D|E|STOP|CRISIS</category>
  <confidence>high|medium|low</confidence>
  <escalation>true|false</escalation>
  <emotion>positive|neutral|negative|angry</emotion>
</intent>
<thinking>[推理过程]</thinking>
"""

_XML_TAG_RE = re.compile(
    r"<intent>.*?<category>(.*?)</category>.*?"
    r"<confidence>(.*?)</confidence>.*?"
    r"<escalation>(.*?)</escalation>.*?"
    r"<emotion>(.*?)</emotion>.*?</intent>",
    re.DOTALL | re.IGNORECASE,
)

_THINKING_RE = re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL | re.IGNORECASE)


class IntentRecognizer:
    """Recognize user intent via LLM with guardrails."""

    def __init__(self, llm_client: Any) -> None:
        self.llm_client = llm_client

    async def recognize(self, user_message: str, context: dict) -> IntentResult:
        """Recognize intent using LLM."""
        prompt = self._build_prompt(user_message, context)
        response = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        raw = response.content if hasattr(response, "content") else str(response)
        return self._parse_response(raw)

    async def recognize_with_guardrails(
        self, user_message: str, session_state: str
    ) -> IntentResult:
        """Recognize with guardrails: keyword fast-path and one-way door lock."""
        # One-way door bypass
        if session_state in {s.value for s in ONE_WAY_DOOR_STATES}:
            return self._fixed_intent_for_state(session_state)

        # Fast-path keyword check
        fast = self._keyword_check(user_message)
        if fast:
            return fast

        return await self.recognize(user_message, {"session_state": session_state})

    def _build_prompt(self, user_message: str, context: dict) -> str:
        """Build the user prompt from context."""
        state = context.get("session_state", "unknown")
        history = context.get("history", [])
        recent = history[-3:] if isinstance(history, list) else []
        history_str = (
            "\n".join(f"  {i + 1}. {h}" for i, h in enumerate(recent)) or "  （无）"
        )
        return (
            f"当前会话状态：{state}\n"
            f"最近3轮对话：\n{history_str}\n"
            f"用户本轮消息：{user_message}\n"
        )

    def _parse_response(self, raw: str) -> IntentResult:
        """Parse XML response from LLM."""
        m = _XML_TAG_RE.search(raw)
        if m:
            cat_str, conf_str, esc_str, emo_str = (s.strip() for s in m.groups())
        else:
            # Fallback: simple line/keyword matching
            cat_str = self._fallback_category(raw)
            conf_str = self._fallback_confidence(raw)
            esc_str = self._fallback_escalation(raw)
            emo_str = self._fallback_emotion(raw)

        category = self._map_category(cat_str)
        confidence = self._map_confidence(conf_str)
        escalation = esc_str.lower() in ("true", "yes", "1")
        emotion = self._map_emotion(emo_str)
        reasoning = self._extract_thinking(raw)

        return IntentResult(
            category=category,
            confidence=confidence,
            escalation=escalation,
            emotion=emotion,
            reasoning=reasoning,
            raw_text=raw,
        )

    def _keyword_check(self, message: str) -> IntentResult | None:
        """Fast-path keyword guardrails."""
        lowered = message.lower()
        # Cooperation fast-path: explicit willingness to pay
        for kw in COOPERATION_KEYWORDS:
            if kw in lowered:
                return IntentResult(
                    category=IntentCategory.COOPERATION,
                    confidence=ConfidenceLevel.HIGH,
                    escalation=False,
                    emotion=EmotionLevel.POSITIVE,
                    reasoning=f"Fast-path cooperation keyword: {kw}",
                )
        for kw in STOP_KEYWORDS:
            if kw in lowered:
                return IntentResult(
                    category=IntentCategory.STOP,
                    confidence=ConfidenceLevel.HIGH,
                    escalation=False,
                    emotion=EmotionLevel.NEGATIVE,
                    reasoning=f"Fast-path keyword match: {kw}",
                )
        for kw in CRISIS_KEYWORDS:
            if kw in lowered:
                return IntentResult(
                    category=IntentCategory.CRISIS,
                    confidence=ConfidenceLevel.HIGH,
                    escalation=True,
                    emotion=EmotionLevel.NEGATIVE,
                    reasoning=f"Fast-path keyword match: {kw}",
                )
        return None

    def _fixed_intent_for_state(self, session_state: str) -> IntentResult:
        """Return fixed intent when session is locked in a one-way door state."""
        mapping = {
            "escalated": (IntentCategory.COMPLAINT, True, EmotionLevel.ANGRY),
            "stopped": (IntentCategory.STOP, False, EmotionLevel.NEGATIVE),
            "crisis": (IntentCategory.CRISIS, True, EmotionLevel.NEGATIVE),
            "disputed": (IntentCategory.DISPUTE, True, EmotionLevel.NEGATIVE),
        }
        cat, esc, emo = mapping.get(
            session_state, (IntentCategory.UNKNOWN, False, EmotionLevel.NEUTRAL)
        )
        return IntentResult(
            category=cat,
            confidence=ConfidenceLevel.HIGH,
            escalation=esc,
            emotion=emo,
            reasoning=f"One-way door state locked: {session_state}",
        )

    def _map_category(self, val: str) -> IntentCategory:
        val = val.strip().upper()
        mapping = {
            "A": IntentCategory.COOPERATION,
            "B": IntentCategory.NEGOTIATION,
            "C": IntentCategory.AVOIDANCE,
            "D": IntentCategory.DISPUTE,
            "E": IntentCategory.COMPLAINT,
            "STOP": IntentCategory.STOP,
            "CRISIS": IntentCategory.CRISIS,
        }
        return mapping.get(val, IntentCategory.UNKNOWN)

    def _map_confidence(self, val: str) -> ConfidenceLevel:
        val = val.strip().lower()
        mapping = {
            "high": ConfidenceLevel.HIGH,
            "medium": ConfidenceLevel.MEDIUM,
            "low": ConfidenceLevel.LOW,
        }
        return mapping.get(val, ConfidenceLevel.LOW)

    def _map_emotion(self, val: str) -> EmotionLevel:
        val = val.strip().lower()
        mapping = {
            "positive": EmotionLevel.POSITIVE,
            "neutral": EmotionLevel.NEUTRAL,
            "negative": EmotionLevel.NEGATIVE,
            "angry": EmotionLevel.ANGRY,
        }
        return mapping.get(val, EmotionLevel.NEUTRAL)

    def _fallback_category(self, raw: str) -> str:
        raw_up = raw.upper()
        for token, cat in [
            ("CRISIS", "CRISIS"),
            ("STOP", "STOP"),
            ("投诉", "E"),
            ("威胁", "E"),
            ("争议", "D"),
            ("质疑", "D"),
            ("回避", "C"),
            ("协商", "B"),
            ("困难", "B"),
            ("合作", "A"),
            ("还款", "A"),
        ]:
            if token in raw_up:
                return cat
        # Also check for bare letter mentions
        for letter in ["A", "B", "C", "D", "E"]:
            if re.search(rf"\b{letter}\b", raw_up):
                return letter
        return "unknown"

    def _fallback_confidence(self, raw: str) -> str:
        if "置信度" in raw or "confidence" in raw.lower():
            if "高" in raw or "high" in raw.lower():
                return "high"
            if "低" in raw or "low" in raw.lower():
                return "low"
        return "medium"

    def _fallback_escalation(self, raw: str) -> str:
        if (
            "escalation" in raw.lower() or "升级" in raw or "上报" in raw
        ) and ("true" in raw.lower() or "是" in raw or "需要" in raw):
            return "true"
        return "false"

    def _fallback_emotion(self, raw: str) -> str:
        if "angry" in raw.lower() or "愤怒" in raw or "生气" in raw:
            return "angry"
        if "positive" in raw.lower() or "积极" in raw or "愿意" in raw:
            return "positive"
        if "negative" in raw.lower() or "消极" in raw or "负面" in raw:
            return "negative"
        return "neutral"

    def _extract_thinking(self, raw: str) -> str:
        m = _THINKING_RE.search(raw)
        if m:
            return m.group(1).strip()
        # Fallback: return first 500 chars if no thinking tag
        return raw[:500].strip()
