from src.llm.base import LLMClient, LLMResponse


class MockLLMClient(LLMClient):
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        return LLMResponse(content="[Mock response]")

    async def detect_intent(self, user_message: str, context: dict) -> str:
        text = user_message.lower()
        if "还" in text or "付" in text:
            return "willing_to_pay"
        if "不" in text or "没钱" in text:
            return "unwilling_to_pay"
        return "ineffective_contact"

    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        name = context.get("user_name", "用户")
        return f"您好{name}，请尽快处理您的逾期账单。"
