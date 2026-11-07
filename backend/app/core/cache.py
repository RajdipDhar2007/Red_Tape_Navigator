"""Tiny async cache: Redis when REDIS_URL is set, otherwise in-process. Never stores sensitive values."""
import json
import time
from typing import Any

from app.core.config import get_settings


class MemoryCache:
    def __init__(self) -> None:
        self._d: dict[str, tuple[float, str]] = {}

    async def get(self, key: str) -> Any | None:
        item = self._d.get(key)
        if not item or item[0] < time.monotonic():
            self._d.pop(key, None)
            return None
        return json.loads(item[1])

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        self._d[key] = (time.monotonic() + ttl, json.dumps(value))

    async def delete(self, key: str) -> None:
        self._d.pop(key, None)


class RedisCache:  # pragma: no cover - needs Redis
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._r = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        raw = await self._r.get(key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        await self._r.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)


_cache: MemoryCache | RedisCache | None = None


def get_cache() -> MemoryCache | RedisCache:
    global _cache
    if _cache is None:
        url = get_settings().redis_url
        _cache = RedisCache(url) if url else MemoryCache()
    return _cache
