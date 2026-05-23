from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from src.llm.base import LLMResponse
from src.llm.clients import (
    ClaudeClient,
    DeepSeekClient,
    MockLLMClient,
    OpenAIClient,
    create_llm_client,
)


@pytest.fixture
def mock_client():
    return MockLLMClient()


@pytest.mark.asyncio
async def test_mock_chat(mock_client):
    resp = await mock_client.chat([{"role": "user", "content": "hello"}])
    assert isinstance(resp, LLMResponse)
    assert resp.content == "[Mock response]"


@pytest.mark.asyncio
async def test_mock_detect_intent(mock_client):
    intent = await mock_client.detect_intent("我要还款", {})
    assert intent == "willing_to_pay"


@pytest.mark.asyncio
async def test_mock_generate_strategy(mock_client):
    resp = await mock_client.generate_strategy_response(
        {"type": "reminder"}, {"user_name": "张三"}
    )
    assert "张三" in resp


# --- ClaudeClient tests ---


@pytest.mark.asyncio
async def test_claude_chat_success():
    client = ClaudeClient(api_key="test-key")
    mock_response = {
        "content": [{"text": "Hello from Claude"}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "model": "claude-sonnet-4-6",
    }

    with respx.mock:
        route = respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        resp = await client.chat([{"role": "user", "content": "hi"}])
        assert resp.content == "Hello from Claude"
        assert resp.usage["input_tokens"] == 10
        assert resp.model == "claude-sonnet-4-6"
        assert route.called


@pytest.mark.asyncio
async def test_claude_chat_retry_on_failure():
    client = ClaudeClient(api_key="test-key")
    mock_response = {
        "content": [{"text": "Hello after retry"}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "model": "claude-sonnet-4-6",
    }

    with respx.mock:
        route = respx.post("https://api.anthropic.com/v1/messages").mock(
            side_effect=[
                httpx.Response(500, text="Server error"),
                httpx.Response(200, json=mock_response),
            ]
        )
        resp = await client.chat([{"role": "user", "content": "hi"}])
        assert resp.content == "Hello after retry"
        assert route.call_count == 2


@pytest.mark.asyncio
async def test_claude_chat_raises_after_two_failures():
    client = ClaudeClient(api_key="test-key")

    with respx.mock:
        route = respx.post("https://api.anthropic.com/v1/messages").mock(
            side_effect=[
                httpx.Response(500, text="Server error"),
                httpx.Response(500, text="Server error"),
            ]
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.chat([{"role": "user", "content": "hi"}])
        assert route.call_count == 2


@pytest.mark.asyncio
async def test_claude_detect_intent():
    client = ClaudeClient(api_key="test-key")

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = LLMResponse(content="willing_to_pay")
        intent = await client.detect_intent("我要还款", {})
        assert intent == "willing_to_pay"
        mock_chat.assert_called_once()
        messages = mock_chat.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert "intent classifier" in messages[0]["content"].lower()


@pytest.mark.asyncio
async def test_claude_generate_strategy_response():
    client = ClaudeClient(api_key="test-key")

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = LLMResponse(content="请尽快还款")
        resp = await client.generate_strategy_response(
            {"type": "reminder"}, {"user_name": "张三"}
        )
        assert resp == "请尽快还款"
        mock_chat.assert_called_once()
        messages = mock_chat.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert "debt collection assistant" in messages[0]["content"].lower()


# --- OpenAIClient tests ---


@pytest.mark.asyncio
async def test_openai_chat_success():
    client = OpenAIClient(api_key="test-key")
    mock_response = {
        "choices": [{"message": {"content": "Hello from OpenAI"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "model": "gpt-4o",
    }

    with respx.mock:
        route = respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        resp = await client.chat([{"role": "user", "content": "hi"}])
        assert resp.content == "Hello from OpenAI"
        assert resp.usage["total_tokens"] == 15
        assert resp.model == "gpt-4o"
        assert route.called


@pytest.mark.asyncio
async def test_openai_detect_intent():
    client = OpenAIClient(api_key="test-key")

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = LLMResponse(content="unwilling_to_pay")
        intent = await client.detect_intent("我没钱", {})
        assert intent == "unwilling_to_pay"


@pytest.mark.asyncio
async def test_openai_generate_strategy_response():
    client = OpenAIClient(api_key="test-key")

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = LLMResponse(content="请尽快处理")
        resp = await client.generate_strategy_response(
            {"type": "urgent"}, {"user_name": "李四"}
        )
        assert resp == "请尽快处理"


# --- DeepSeekClient tests ---


@pytest.mark.asyncio
async def test_deepseek_chat_success():
    client = DeepSeekClient(api_key="test-key")
    mock_response = {
        "choices": [{"message": {"content": "Hello from DeepSeek"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "model": "deepseek-chat",
    }

    with respx.mock:
        route = respx.post("https://api.deepseek.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        resp = await client.chat([{"role": "user", "content": "hi"}])
        assert resp.content == "Hello from DeepSeek"
        assert resp.usage["total_tokens"] == 15
        assert resp.model == "deepseek-chat"
        assert route.called


@pytest.mark.asyncio
async def test_deepseek_detect_intent():
    client = DeepSeekClient(api_key="test-key")

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = LLMResponse(content="complaint")
        intent = await client.detect_intent("我要投诉", {})
        assert intent == "complaint"


@pytest.mark.asyncio
async def test_deepseek_generate_strategy_response():
    client = DeepSeekClient(api_key="test-key")

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = LLMResponse(content="我们会尽快处理")
        resp = await client.generate_strategy_response(
            {"type": "follow_up"}, {"user_name": "王五"}
        )
        assert resp == "我们会尽快处理"


# --- Factory tests ---


def test_factory_mock():
    client = create_llm_client({"provider": "mock"})
    assert isinstance(client, MockLLMClient)


def test_factory_claude():
    client = create_llm_client({"provider": "claude", "api_key": "key"})
    assert isinstance(client, ClaudeClient)
    assert client.model == "claude-sonnet-4-6"


def test_factory_openai():
    client = create_llm_client({"provider": "openai", "api_key": "key"})
    assert isinstance(client, OpenAIClient)
    assert client.model == "gpt-4o"


def test_factory_deepseek():
    client = create_llm_client({"provider": "deepseek", "api_key": "key"})
    assert isinstance(client, DeepSeekClient)
    assert client.model == "deepseek-chat"


def test_factory_custom_model():
    client = create_llm_client({"provider": "openai", "api_key": "key", "model": "gpt-4"})
    assert isinstance(client, OpenAIClient)
    assert client.model == "gpt-4"


def test_factory_unknown_provider():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_llm_client({"provider": "unknown", "api_key": "key"})
