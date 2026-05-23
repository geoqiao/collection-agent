from typing import Literal

from src.core.models import Message

ContextStrategy = Literal["sliding_window", "summarize", "relevance"]


class ContextWindow:
    def __init__(
        self,
        max_messages: int = 50,
        max_tokens: int = 4096,
        strategy: ContextStrategy = "sliding_window",
    ):
        self._messages: list[Message] = []
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.strategy = strategy
        self._summary: str = ""

    def add_message(self, message: Message) -> None:
        """Add message and apply window management."""
        self._messages.append(message)
        self._apply_strategy()

    def get_messages(self) -> list[Message]:
        """Get current messages in window."""
        return list(self._messages)

    def get_messages_for_llm(self, max_tokens: int | None = None) -> list[dict[str, str]]:
        """Return messages formatted for LLM API."""
        _max_t = max_tokens or self.max_tokens
        messages = self._messages[-self.max_messages:]
        result = []
        if self._summary:
            result.append({"role": "system", "content": f"Previous conversation summary: {self._summary}"})
        for msg in messages:
            role = "assistant" if msg.direction == "outbound" else "user"
            result.append({"role": role, "content": msg.content})
        return result

    def _apply_strategy(self) -> None:
        if self.strategy == "sliding_window":
            if len(self._messages) > self.max_messages:
                self._messages = self._messages[-self.max_messages:]
        elif self.strategy == "summarize":
            if len(self._messages) > self.max_messages:
                # Simple summary: keep first 5, last max_messages-5, summarize middle
                to_summarize = self._messages[5:-(self.max_messages - 5)]
                self._summary = self._summarize_messages(to_summarize)
                self._messages = self._messages[:5] + self._messages[-(self.max_messages - 5):]

    def _summarize_messages(self, messages: list[Message]) -> str:
        """Generate simple summary of messages."""
        intents = set()
        for msg in messages:
            if hasattr(msg, 'metadata') and msg.metadata.get('intent'):
                intents.add(msg.metadata['intent'])
        if intents:
            return f"User expressed: {', '.join(intents)}"
        return f"{len(messages)} messages exchanged"

    def clear(self) -> None:
        self._messages.clear()
        self._summary = ""

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def is_full(self) -> bool:
        return len(self._messages) >= self.max_messages
