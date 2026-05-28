"""Tool registry with @tool decorator.

Tools are async functions, not ABC subclasses.
Schema is auto-derived from type hints.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolInfo:
    """Metadata for a registered tool."""

    name: str
    description: str
    func: Callable
    schema: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Registry for tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolInfo] = {}

    def register(self, info: ToolInfo) -> None:
        self._tools[info.name] = info

    def get(self, name: str) -> ToolInfo | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolInfo]:
        return list(self._tools.values())

    def get_schema(self, name: str) -> dict[str, Any]:
        tool = self._tools.get(name)
        return tool.schema if tool else {}


# Global registry instance
_GLOBAL_REGISTRY = ToolRegistry()


def tool(name: str, description: str) -> Callable:
    """Decorator to register a tool.

    Usage:
        @tool(name="query_bill", description="Query user bill")
        async def query_bill(user_id: str, store: Store) -> dict:
            ...
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        hints = getattr(func, "__annotations__", {})

        properties: dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("store", "compliance", "config"):
                # Skip injected dependencies
                continue

            param_type = hints.get(param_name, str)
            json_type = _python_type_to_json(param_type)

            properties[param_name] = {
                "type": json_type,
                "description": f"Parameter {param_name}",
            }

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

        info = ToolInfo(name=name, description=description, func=func, schema=schema)
        _GLOBAL_REGISTRY.register(info)

        # Attach registry reference for convenience
        func._tool_info = info  # type: ignore[attr-defined]
        return func

    return decorator


def _python_type_to_json(py_type: type) -> str:
    """Map Python types to JSON Schema types."""
    origin = getattr(py_type, "__origin__", None)
    if origin is not None:
        py_type = origin

    mapping = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    return mapping.get(py_type, "string")


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _GLOBAL_REGISTRY
