"""Tool registry for managing and discovering tools."""

from __future__ import annotations

from typing import Any

from collect_agent.tools.base import Tool


class ToolRegistry:
    """Registry for collecting and retrieving tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_xml_descriptions(self) -> str:
        """Return concatenated XML descriptions of all registered tools."""
        return "\n".join(tool.to_xml_description() for tool in self._tools.values())
