"""Tool framework base classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolParameter:
    name: str
    param_type: str  # "string", "number", "boolean", "array"
    description: str
    required: bool = True
    enum: list[Any] | None = None


@dataclass
class ToolResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Tool(ABC):
    name: str = ""
    description: str = ""
    parameters: list[ToolParameter] = field(default_factory=list)

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        pass

    def to_schema(self) -> dict[str, Any]:
        """Return JSON Schema for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        p.name: {
                            "type": p.param_type,
                            "description": p.description,
                            **({"enum": p.enum} if p.enum else {}),
                        }
                        for p in self.parameters
                    },
                    "required": [p.name for p in self.parameters if p.required],
                },
            },
        }

    def to_xml_description(self) -> str:
        """Return compact XML description for prompt injection."""
        lines = [f'<tool name="{self.name}">']
        lines.append(f"  <description>{self.description}</description>")
        for p in self.parameters:
            req = " required" if p.required else ""
            lines.append(f'  <parameter name="{p.name}" type="{p.param_type}"{req}>{p.description}</parameter>')
        lines.append("</tool>")
        return "\n".join(lines)
