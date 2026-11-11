"""Free LLM providers (Ollama, Gemini): native JSON-schema output, validation, and provider selection. No real network."""
import json

import httpx
import pytest
from pydantic import BaseModel

from app.agent.llm import LLM, LLMUnavailable
from app.core.config import get_settings


class Answer(BaseModel):
    city: str
    activity: str


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("OLLAMA_MODEL", "GEMINI_API_KEY", "GEMINI_MODEL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "LLM_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_nothing_configured_is_unavailable():
    llm = LLM()
    assert llm.provider == "none" and not llm.available


async def test_ollama_structured_output(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "local-model")
    get_settings.cache_clear()
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"message": {"content": json.dumps({"city": "Kolkata", "activity": "bakery"})}})

    llm = LLM(http=_client(handler))
    assert llm.provider == "ollama" and llm.available
    out = await llm.structured("sys", "user", Answer)
    assert out == Answer(city="Kolkata", activity="bakery")
    assert seen["url"].endswith("/api/chat")
    assert seen["body"]["model"] == "local-model" and seen["body"]["stream"] is False
    assert seen["body"]["format"]["properties"]["city"]  # the schema is sent as a JSON-schema constraint
    assert seen["body"]["messages"][0] == {"role": "system", "content": "sys"}


async def test_gemini_structured_output_sends_key_in_header_only(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "some-model")
    get_settings.cache_clear()
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["key"] = req.headers.get("x-goog-api-key")
        seen["body"] = json.loads(req.content)
        text = json.dumps({"city": "Delhi", "activity": "gym"})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    llm = LLM(http=_client(handler))
    assert llm.provider == "gemini" and llm.available
    out = await llm.structured("sys", "user", Answer)
    assert out.city == "Delhi"
    assert "test-key" not in seen["url"] and seen["key"] == "test-key"
    assert seen["url"].startswith("https://generativelanguage.googleapis.com/")
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"


async def test_invalid_model_output_is_rejected(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "m")
    get_settings.cache_clear()

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": json.dumps({"city": 5})}})

    with pytest.raises(ValueError, match="failed validation"):
        await LLM(http=_client(handler)).structured("s", "u", Answer)


async def test_provider_switch_and_tool_loop_limits(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "m")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("GEMINI_MODEL", "g")
    get_settings.cache_clear()
    assert LLM(provider="gemini").provider == "gemini"
    assert LLM(provider="none").provider == "none"
    assert LLM().provider == "ollama"  # auto prefers the local, free model
    with pytest.raises(LLMUnavailable):
        await LLM().tool_loop("s", "u", [])


async def test_provider_transport_refuses_other_hosts(monkeypatch):
    from app.core.llm_http import LLMEndpointRejected, post_json

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    get_settings.cache_clear()
    with pytest.raises(LLMEndpointRejected):
        await post_json("https://example.gov.in/apply", {"x": 1})  # a portal-like address must never be reachable
