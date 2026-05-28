"""Skill executor with JSON ReAct loop.

Actions: tool_call | reply | escalate
NO 'end' action — collection agents never "naturally end" a conversation.
"""

from __future__ import annotations

import json
from typing import Any

from collect_agent.core.context import Context
from collect_agent.llm.base import LLMClient
from collect_agent.skills.base import Skill, SkillResult
from collect_agent.tools.registry import ToolRegistry


class SkillExecutor:
    """Executes skills using a ReAct loop driven by an LLM."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
    ) -> None:
        self._llm = llm_client
        self._tools = tool_registry

    async def execute(
        self,
        skill: Skill,
        context: Context,
        state: Any,
    ) -> SkillResult:
        """Execute a skill using the ReAct loop.

        1. Build initial observation from Context
        2. For up to skill.max_steps:
           a. Call LLM to think and decide action
           b. Parse JSON action
           c. If reply: audit + return SkillResult
           d. If tool_call: execute tool, add result as new observation
           e. If escalate: return escalation result
        3. If max steps reached: return error fallback
        """
        observations = self._build_observation(context)
        messages = self._build_messages(skill, observations)

        for step in range(skill.max_steps):
            response = await self._llm.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            content = response.content if hasattr(response, "content") else str(response)

            action = self._parse_action(content)

            if action["type"] == "reply":
                return SkillResult(
                    status="success",
                    response_text=action.get("text", ""),
                    thinking=action.get("thinking", ""),
                )

            elif action["type"] == "tool_call":
                tool_name = action.get("name", "")
                parameters = action.get("parameters", {})

                result = await self._call_tool(tool_name, parameters, state)

                # Add tool result as new observation
                tool_result_msg = (
                    f"Tool '{tool_name}' result: {json.dumps(result, ensure_ascii=False)}"
                )
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": tool_result_msg})

            elif action["type"] == "escalate":
                return SkillResult(
                    status="needs_escalation",
                    response_text=action.get("text", ""),
                    new_session_state="escalated",
                    escalation=True,
                    thinking=action.get("thinking", ""),
                )

            else:
                # Unknown action type — continue with feedback
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Unknown action type: {action['type']}. "
                        "Please use one of: tool_call, reply, escalate.",
                    }
                )

        # Max steps reached
        return SkillResult(
            status="error",
            response_text="系统繁忙，请稍后重试。",
            thinking=f"Max ReAct steps ({skill.max_steps}) reached.",
        )

    def _build_observation(self, context: Context) -> str:
        """Build initial observation string from Context."""
        return context.to_prompt()

    def _build_messages(
        self,
        skill: Skill,
        observations: str,
    ) -> list[dict[str, str]]:
        """Build messages for LLM chat."""
        system_prompt = self._build_system_prompt(skill)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": observations},
        ]

    def _build_system_prompt(self, skill: Skill) -> str:
        """Build system prompt for the ReAct loop."""
        skill_prompt = skill.get_system_prompt()

        # Build available tools schema
        tool_schemas = []
        for tool_name in skill.tools:
            info = self._tools.get(tool_name)
            if info:
                tool_schemas.append(json.dumps(info.schema, ensure_ascii=False, indent=2))

        tools_section = (
            "\n\n## 可用工具 Schema\n"
            + "\n".join(tool_schemas)
            if tool_schemas
            else ""
        )

        action_format = """
## ReAct 动作格式
你必须用 JSON 格式输出思考过程和动作：

```json
{
  "type": "tool_call",
  "thinking": "你的推理过程",
  "name": "tool_name",
  "parameters": {"param1": "value1"}
}
```

或：

```json
{
  "type": "reply",
  "thinking": "你的推理过程",
  "text": "回复用户的内容"
}
```

或：

```json
{
  "type": "escalate",
  "thinking": "你的推理过程",
  "text": "升级原因"
}
```

注意：
- 不要使用 "end" 动作 — 催收对话不存在自然结束
- 如果需要结束当前轮次，使用 "reply" 并输出回复内容
- 所有金额、日期必须从 <facts> 中读取，禁止编造
"""

        return f"{skill_prompt}{tools_section}\n{action_format}"

    def _parse_action(self, content: str) -> dict[str, Any]:
        """Parse action from JSON format.

        Tries to extract JSON from code blocks or raw text.
        """
        # Try code block first
        if "```json" in content:
            start = content.find("```json") + len("```json")
            end = content.find("```", start)
            if end != -1:
                json_str = content[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

        # Try raw JSON
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass

        return {"type": "unknown", "raw": content}

    async def _call_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        state: Any,
    ) -> dict[str, Any]:
        """Execute a tool by name."""
        info = self._tools.get(tool_name)
        if info is None:
            return {"error": f"Tool '{tool_name}' not found"}

        # Inject store from state if needed
        # This is a simplified dependency injection for MVP
        from collect_agent.storage.memory_store import MemoryStore
        from collect_agent.storage.sqlite_store import SQLiteStore

        store = getattr(state, "_store", None)
        if store is None:
            # Try to find store from session
            store = state

        # Build kwargs with store injection
        kwargs = dict(parameters)
        import inspect
        sig = inspect.signature(info.func)

        for param_name in sig.parameters:
            if param_name == "store":
                kwargs["store"] = store

        try:
            result = await info.func(**kwargs)
            if isinstance(result, dict):
                return result
            return {"data": str(result)}
        except Exception as e:
            return {"error": str(e)}
