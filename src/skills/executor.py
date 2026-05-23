"""Skill executor with ReAct loop."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from src.llm.base import LLMClient
from src.prompts.engine import PromptEngine
from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord
from src.tools._safe_xml import safe_xml_fromstring
from src.tools.base import ToolResult
from src.tools.registry import ToolRegistry


class SkillExecutor:
    """Executes skills using a ReAct (Reasoning + Acting) loop driven by an LLM."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        prompt_engine: PromptEngine | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.prompt_engine = prompt_engine or PromptEngine()

    async def execute(self, skill: Skill, ctx: SkillContext) -> SkillResult:
        """Execute a skill using the ReAct loop.

        1. Build initial observation from SkillContext
        2. For up to skill.max_react_steps (default 5):
           a. Call LLM to think about current state and decide action
           b. Parse action (reply / tool_call / escalate / end)
           c. If reply: return SkillResult with response_text
           d. If tool_call: execute tool, add result as new observation
           e. If escalate: return escalation result
           f. If end: return result with no response
        3. If max steps reached: return error fallback
        """
        actions: list[ToolCallRecord] = []
        observations = self._build_observation(ctx)
        max_steps = skill.max_react_steps

        for step in range(max_steps):
            # Build messages for LLM
            messages = self._build_messages(skill, ctx, observations, actions)

            # Call LLM to get thought + action
            llm_response = await self.llm_client.chat(messages)
            content = llm_response.content

            # Parse action from XML
            action_type, action_data = self._parse_action(content)

            if action_type == "reply":
                response_text = action_data.get("text", "")
                return SkillResult(
                    status=SkillResultStatus.SUCCESS,
                    response_text=response_text,
                    actions=actions,
                    thinking=content,
                )

            elif action_type == "tool_call":
                tool_calls = action_data.get("tool_calls", [])
                for tc in tool_calls:
                    tool_name = tc.get("name", "")
                    parameters = tc.get("parameters", {})

                    tool = self.tool_registry.get(tool_name)
                    if tool is None:
                        result_data = {"error": f"Tool '{tool_name}' not found"}
                        tool_result = ToolResult(success=False, error=result_data["error"])
                    else:
                        tool_result = await tool.execute(**parameters)
                        result_data = tool_result.data if tool_result.success else {"error": tool_result.error or "Unknown error"}

                    actions.append(ToolCallRecord(
                        tool_name=tool_name,
                        parameters=parameters,
                        result=result_data,
                    ))

                    # Add tool result as new observation
                    observations += f"\nTool '{tool_name}' result: {result_data}"

            elif action_type == "escalate":
                return SkillResult(
                    status=SkillResultStatus.NEEDS_ESCALATION,
                    response_text=action_data.get("text"),
                    actions=actions,
                    escalation=True,
                    thinking=content,
                )

            elif action_type == "end":
                return SkillResult(
                    status=SkillResultStatus.STOPPED,
                    actions=actions,
                    thinking=content,
                )

            # Unknown action type - continue to next step
            observations += f"\nUnknown action type: {action_type}. Continuing..."

        # Max steps reached
        return SkillResult(
            status=SkillResultStatus.ERROR,
            response_text="I apologize, but I'm unable to complete this request at the moment.",
            actions=actions,
            thinking=f"Max ReAct steps ({max_steps}) reached.",
        )

    def _build_observation(self, ctx: SkillContext) -> str:
        """Build initial observation string from SkillContext."""
        parts = [
            f"User ID: {ctx.user_id}",
            f"User Name: {ctx.user_profile.name}",
            f"Overdue Days: {ctx.user_profile.overdue_days}",
            f"Amount Due: {ctx.user_profile.amount_due}",
            f"Current Intent: {ctx.current_intent}",
            f"Session State: {ctx.session_state}",
            f"Negotiation Round: {ctx.negotiation_round}",
        ]
        if ctx.user_message:
            parts.append(f"User Message: {ctx.user_message}")
        if ctx.bill_facts:
            parts.append(f"Bill Facts: {ctx.bill_facts}")
        if ctx.memory:
            parts.append(f"Memory: {ctx.memory}")
        return "\n".join(parts)

    def _build_messages(
        self,
        skill: Skill,
        ctx: SkillContext,
        observations: str,
        actions: list[ToolCallRecord],
    ) -> list[dict[str, str]]:
        """Build messages for LLM chat."""
        system_prompt = self._build_system_prompt(skill, ctx)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": observations},
        ]

        # Add previous actions as assistant/user turns
        for record in actions:
            messages.append({
                "role": "assistant",
                "content": f"<action>\n  <type>tool_call</type>\n  <tool_calls>\n    <tool_call>\n      <name>{record.tool_name}</name>\n      <parameters>{record.parameters}</parameters>\n    </tool_call>\n  </tool_calls>\n</action>",
            })
            messages.append({
                "role": "user",
                "content": f"Tool '{record.tool_name}' result: {record.result}",
            })

        return messages

    def _build_system_prompt(self, skill: Skill, ctx: SkillContext) -> str:
        """Build system prompt for the ReAct loop.

        If the skill has a prompt_template, use PromptEngine to assemble
        the full prompt from template fragments. Otherwise fall back to
        a minimal default prompt.
        """
        if skill.prompt_template and self.prompt_engine:
            context = {
                "skill_name": skill.name,
                "skill_description": skill.description,
                "user_id": ctx.user_id,
                "user_profile": ctx.user_profile,
                "session_state": ctx.session_state,
                "intent_category": ctx.current_intent,
                "conversation_history": ctx.conversation_history,
                "bill_facts": ctx.bill_facts,
                "available_tools": skill.get_available_tools(),
            }
            assembled = self.prompt_engine.assemble_skill_prompt(
                skill.prompt_template.replace(".xml", "").replace(".md", ""),
                context,
            )
            if assembled.strip():
                # Append the XML action schema since templates may not include it
                assembled += (
                    "\n\n## ReAct 动作格式\n"
                    "你必须用 XML 格式输出思考过程和动作：\n"
                    "<action>\n"
                    "  <type>reply|tool_call|escalate|end</type>\n"
                    "  <!-- reply: 直接回复用户 -->\n"
                    "  <text>回复内容</text>\n"
                    "  <!-- tool_call: 调用一个或多个工具 -->\n"
                    "  <tool_calls>\n"
                    "    <tool_call>\n"
                    "      <name>tool_name</name>\n"
                    "      <parameters>\n"
                    "        <param_name>value</param_name>\n"
                    "      </parameters>\n"
                    "    </tool_call>\n"
                    "  </tool_calls>\n"
                    "  <!-- escalate: 升级人工 -->\n"
                    "  <text>升级原因</text>\n"
                    "</action>"
                )
                return assembled

        # Fallback minimal prompt
        lines = [
            f"You are a debt collection agent skill: {skill.name}",
            f"Description: {skill.description}",
            "",
            "Available tools:",
        ]

        for tool in skill.get_available_tools():
            lines.append(tool.to_xml_description())

        lines.extend([
            "",
            "You must respond with an XML action block. Possible action types:",
            "- reply: Respond to the user",
            "- tool_call: Call one or more tools",
            "- escalate: Escalate to a human agent",
            "- end: End the conversation without responding",
            "",
            "Format:",
            "<action>",
            "  <type>reply|tool_call|escalate|end</type>",
            "  <!-- For reply: -->",
            "  <text>Your response here</text>",
            "  <!-- For tool_call: -->",
            "  <tool_calls>",
            "    <tool_call>",
            "      <name>tool_name</name>",
            "      <parameters>",
            "        <param_name>value</param_name>",
            "      </parameters>",
            "    </tool_call>",
            "  </tool_calls>",
            "  <!-- For escalate: -->",
            "  <text>Reason for escalation</text>",
            "</action>",
        ])

        return "\n".join(lines)

    def _parse_action(self, xml_text: str) -> tuple[str, dict[str, Any]]:
        """Parse action from XML format.

        Returns (action_type, action_data dict).
        """
        # Extract action block from potentially larger text
        start = xml_text.find("<action>")
        end = xml_text.find("</action>")
        if start == -1 or end == -1:
            return "unknown", {"raw": xml_text}

        action_xml = xml_text[start:end + len("</action>")]

        try:
            root = safe_xml_fromstring(action_xml)
        except (ET.ParseError, ValueError):
            return "unknown", {"raw": xml_text}

        action_type_elem = root.find("type")
        action_type = action_type_elem.text.strip() if action_type_elem is not None and action_type_elem.text else "unknown"

        data: dict[str, Any] = {}

        if action_type == "reply":
            text_elem = root.find("text")
            data["text"] = text_elem.text.strip() if text_elem is not None and text_elem.text else ""

        elif action_type == "tool_call":
            tool_calls: list[dict[str, Any]] = []
            tool_calls_elem = root.find("tool_calls")
            if tool_calls_elem is not None:
                for tc_elem in tool_calls_elem.findall("tool_call"):
                    name_elem = tc_elem.find("name")
                    params_elem = tc_elem.find("parameters")

                    tool_name = name_elem.text.strip() if name_elem is not None and name_elem.text else ""
                    parameters: dict[str, Any] = {}

                    if params_elem is not None:
                        for child in params_elem:
                            parameters[child.tag] = child.text.strip() if child.text else ""

                    tool_calls.append({"name": tool_name, "parameters": parameters})

            data["tool_calls"] = tool_calls

        elif action_type == "escalate":
            text_elem = root.find("text")
            data["text"] = text_elem.text.strip() if text_elem is not None and text_elem.text else ""

        elif action_type == "end":
            pass  # No additional data needed

        return action_type, data
