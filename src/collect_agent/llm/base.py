from abc import ABC, abstractmethod
from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    usage: dict[str, int] = {}
    model: str = ""


class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def detect_intent(self, user_message: str, context: dict) -> str:
        pass

    @abstractmethod
    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        pass
