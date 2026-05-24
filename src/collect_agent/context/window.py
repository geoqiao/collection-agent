from typing import Literal

from collect_agent.core.models import Message

ContextStrategy = Literal["sliding_window", "summarize", "relevance"]


def estimate_tokens(text: str) -> int:
    """Estimate token count for mixed CJK/English text.

    Approximation rules:
    - CJK characters (一-鿿): ~1 token each
    - ASCII letters/numbers: ~0.25 tokens per char (4 chars ≈ 1 token)
    - Other symbols/spaces: ~0.5 tokens per char
    """
    if not text:
        return 0

    total = 0
    for ch in text:
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            # CJK Unified Ideographs
            total += 1
        elif ch.isascii() and ch.isalnum():
            # ASCII alphanumeric
            total += 0.25
        else:
            # Symbols, spaces, punctuation, other scripts
            total += 0.5

    return int(total) + 1  # +1 for rounding up


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

    def get_messages_for_llm(
        self, max_tokens: int | None = None
    ) -> list[dict[str, str]]:
        """Return messages formatted for LLM API, truncated by token limit."""
        _max_t = max_tokens or self.max_tokens
        # Start with summary if available
        result: list[dict[str, str]] = []
        token_count = 0

        if self._summary:
            summary_msg = {
                "role": "system",
                "content": f"Previous conversation summary: {self._summary}",
            }
            result.append(summary_msg)
            token_count += estimate_tokens(summary_msg["content"])

        # Select messages from recent to oldest, respecting token budget
        selected: list[dict[str, str]] = []
        for msg in reversed(self._messages):
            role = "assistant" if msg.direction == "outbound" else "user"
            formatted = {"role": role, "content": msg.content}
            msg_tokens = estimate_tokens(msg.content)

            # Reserve 50 tokens for overhead / safety margin
            if token_count + msg_tokens + 50 > _max_t:
                break

            selected.append(formatted)
            token_count += msg_tokens

        # Reverse to maintain chronological order
        result.extend(reversed(selected))
        return result

    def _apply_strategy(self) -> None:
        if self.strategy == "sliding_window":
            # Apply both message count and token count limits
            if len(self._messages) > self.max_messages:
                self._messages = self._messages[-self.max_messages :]
            # Token-based pruning: if total exceeds limit, drop oldest
            total_tokens = sum(estimate_tokens(m.content) for m in self._messages)
            while self._messages and total_tokens > self.max_tokens:
                removed = self._messages.pop(0)
                total_tokens -= estimate_tokens(removed.content)
        elif self.strategy == "summarize":
            if len(self._messages) > self.max_messages:
                # Simple summary: keep first 5, last max_messages-5, summarize middle
                to_summarize = self._messages[5 : -(self.max_messages - 5)]
                self._summary = self._summarize_messages(to_summarize)
                self._messages = (
                    self._messages[:5] + self._messages[-(self.max_messages - 5) :]
                )

    def _summarize_messages(self, messages: list[Message]) -> str:
        """Generate simple summary of messages."""
        intents = set()
        for msg in messages:
            if hasattr(msg, "metadata") and msg.metadata.get("intent"):
                intents.add(msg.metadata["intent"])
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

    @property
    def token_count(self) -> int:
        """Current estimated token count of all messages."""
        return sum(estimate_tokens(m.content) for m in self._messages)
