"""HTTP transport for language-model providers (Ollama, Gemini).

Kept outside `app/agent/` on purpose: the agent package must never contain write requests (a static test enforces that no
code path can post to a government portal). This helper can only reach two kinds of endpoint: the Gemini API host and the
Ollama base URL from configuration, so it cannot be pointed at any other site.
"""
import httpx

from app.core.config import get_settings

GEMINI_HOST = "https://generativelanguage.googleapis.com/"


class LLMEndpointRejected(ValueError):
    pass


def _allowed(endpoint: str) -> bool:
    ollama = get_settings().ollama_base_url.rstrip("/") + "/"
    return endpoint.startswith(GEMINI_HOST) or endpoint.startswith(ollama)


async def post_json(
    endpoint: str, payload: dict, headers: dict | None = None, http: httpx.AsyncClient | None = None, timeout: float = 120
) -> dict:
    if not _allowed(endpoint):
        raise LLMEndpointRejected("endpoint is not a configured language-model provider")
    if http is not None:
        r = await http.post(endpoint, json=payload, headers=headers)
    else:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(endpoint, json=payload, headers=headers)
    r.raise_for_status()
    return r.json()
