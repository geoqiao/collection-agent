import httpx

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


_INTENT_SYSTEM_PROMPT = (
    "You are an intent classifier for a debt collection system. "
    "Classify the user's message into exactly one of these categories: "
    "willing_to_pay, unwilling_to_pay, ineffective_contact, request_info, complaint. "
    "Respond with only the category name, nothing else."
)

_STRATEGY_SYSTEM_PROMPT = (
    "You are a debt collection assistant. Generate a polite, professional response "
    "based on the provided strategy and context. Be concise and respectful."
)


class ClaudeClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        base_url: str = "https://api.anthropic.com",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        url = f"{self.base_url}/v1/messages"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError:
                # Retry once
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

        content = data["content"][0]["text"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            usage={
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            model=data.get("model", self.model),
        )

    async def detect_intent(self, user_message: str, context: dict) -> str:
        messages = [
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        resp = await self.chat(messages, temperature=0.0, max_tokens=64)
        return resp.content.strip().lower()

    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        strategy_text = f"Strategy: {strategy}\nContext: {context}"
        messages = [
            {"role": "system", "content": _STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": strategy_text},
        ]
        resp = await self.chat(messages, temperature=0.7, max_tokens=1024)
        return resp.content


class OpenAIClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            model=data.get("model", self.model),
        )

    async def detect_intent(self, user_message: str, context: dict) -> str:
        messages = [
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        resp = await self.chat(messages, temperature=0.0, max_tokens=64)
        return resp.content.strip().lower()

    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        strategy_text = f"Strategy: {strategy}\nContext: {context}"
        messages = [
            {"role": "system", "content": _STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": strategy_text},
        ]
        resp = await self.chat(messages, temperature=0.7, max_tokens=1024)
        return resp.content


class DeepSeekClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            model=data.get("model", self.model),
        )

    async def detect_intent(self, user_message: str, context: dict) -> str:
        messages = [
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        resp = await self.chat(messages, temperature=0.0, max_tokens=64)
        return resp.content.strip().lower()

    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        strategy_text = f"Strategy: {strategy}\nContext: {context}"
        messages = [
            {"role": "system", "content": _STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": strategy_text},
        ]
        resp = await self.chat(messages, temperature=0.7, max_tokens=1024)
        return resp.content


def create_llm_client(config: dict) -> LLMClient:
    provider = config.get("provider", "mock")
    if provider == "mock":
        return MockLLMClient()
    elif provider == "claude":
        return ClaudeClient(
            api_key=config["api_key"],
            model=config.get("model", "claude-sonnet-4-6"),
            base_url=config.get("base_url", "https://api.anthropic.com"),
        )
    elif provider == "openai":
        return OpenAIClient(
            api_key=config["api_key"],
            model=config.get("model", "gpt-4o"),
            base_url=config.get("base_url", "https://api.openai.com/v1"),
        )
    elif provider == "deepseek":
        return DeepSeekClient(
            api_key=config["api_key"],
            model=config.get("model", "deepseek-chat"),
            base_url=config.get("base_url", "https://api.deepseek.com/v1"),
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
