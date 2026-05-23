"""XML response parser for DeepSeek compatibility."""

import re
import xml.etree.ElementTree as ET
from typing import Any

from src.prompts.schemas import ParsedAction, ParsedIntent, ParsedXMLResponse
from src.tools._safe_xml import safe_xml_fromstring


_INTENT_RE = re.compile(
    r"<intent>.*?<category>(.*?)</category>.*?"
    r"<confidence>(.*?)</confidence>.*?"
    r"<escalation>(.*?)</escalation>.*?"
    r"<emotion>(.*?)</emotion>.*?</intent>",
    re.DOTALL | re.IGNORECASE,
)

_THINKING_RE = re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL | re.IGNORECASE)
_ACTION_TYPE_RE = re.compile(r"<type>(.*?)</type>", re.DOTALL | re.IGNORECASE)
_FINAL_MESSAGE_RE = re.compile(
    r"<final_message>(.*?)</final_message>", re.DOTALL | re.IGNORECASE
)
_TOOL_CALL_RE = re.compile(
    r"<tool_call>.*?<name>(.*?)</name>.*?<parameters>(.*?)</parameters>.*?</tool_call>",
    re.DOTALL | re.IGNORECASE,
)


class XMLResponseParser:
    """Parse XML-structured LLM responses."""

    @staticmethod
    def parse(xml_text: str) -> ParsedXMLResponse:
        """Parse full XML response."""
        return ParsedXMLResponse(
            thinking=XMLResponseParser._extract_thinking(xml_text),
            intent=XMLResponseParser.parse_intent(xml_text),
            action=XMLResponseParser.parse_action(xml_text),
            final_message=XMLResponseParser._extract_final_message(xml_text),
        )

    @staticmethod
    def parse_intent(xml_text: str) -> ParsedIntent:
        """Parse intent block."""
        m = _INTENT_RE.search(xml_text)
        if m:
            cat, conf, esc, emo = (s.strip() for s in m.groups())
            return ParsedIntent(
                category=cat,
                confidence=conf,
                escalation=esc.lower() in ("true", "yes", "1"),
                emotion=emo,
            )
        return ParsedIntent()

    @staticmethod
    def parse_action(xml_text: str) -> ParsedAction:
        """Parse action block."""
        action = ParsedAction()

        # Extract action type
        type_match = _ACTION_TYPE_RE.search(xml_text)
        if type_match:
            action.action_type = type_match.group(1).strip().lower()

        # Extract tool calls
        for tc_match in _TOOL_CALL_RE.finditer(xml_text):
            tool_name = tc_match.group(1).strip()
            params_xml = tc_match.group(2).strip()
            params = XMLResponseParser._parse_parameters(params_xml)
            action.tool_calls.append({"name": tool_name, "parameters": params})

        # Extract final message if present
        msg_match = _FINAL_MESSAGE_RE.search(xml_text)
        if msg_match:
            action.content = msg_match.group(1).strip()

        return action

    @staticmethod
    def _extract_thinking(xml_text: str) -> str:
        m = _THINKING_RE.search(xml_text)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _extract_final_message(xml_text: str) -> str:
        m = _FINAL_MESSAGE_RE.search(xml_text)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _parse_parameters(params_xml: str) -> dict[str, Any]:
        """Parse parameter XML into dict."""
        params: dict[str, Any] = {}
        try:
            # Wrap in root for valid XML
            wrapped = f"<root>{params_xml}</root>"
            root = safe_xml_fromstring(wrapped)
            for child in root:
                text = child.text.strip() if child.text else ""
                # Try int/float conversion
                try:
                    params[child.tag] = int(text)
                except ValueError:
                    try:
                        params[child.tag] = float(text)
                    except ValueError:
                        params[child.tag] = text
        except ET.ParseError:
            # Fallback: regex extract
            param_re = re.compile(r"<(\w+)>(.*?)</\w+>", re.DOTALL)
            for m in param_re.finditer(params_xml):
                params[m.group(1)] = m.group(2).strip()
        return params
