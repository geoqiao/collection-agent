"""Shared test utilities for skills."""

from __future__ import annotations

from collect_agent.llm.base import LLMClient, LLMResponse


class ReActMockLLM(LLMClient):
    """Mock LLM that returns pre-configured XML actions for ReAct loop testing."""

    def __init__(self, actions: list[str]):
        self.actions = actions
        self.index = 0
        self.chat_calls: list[list[dict]] = []

    async def chat(self, messages, temperature=0.7, max_tokens=1024):
        self.chat_calls.append(messages)
        action = self.actions[self.index] if self.index < len(self.actions) else ""
        self.index += 1
        return LLMResponse(content=action)

    async def detect_intent(self, user_message: str, context: dict) -> str:
        return "cooperation"

    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        return "mock response"
