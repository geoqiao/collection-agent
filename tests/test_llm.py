import pytest
from src.llm.base import LLMResponse
from src.llm.clients import MockLLMClient


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
