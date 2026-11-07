"""Tiny async cache: Redis when REDIS_URL is set, otherwise in-process. Never stores sensitive values."""
import json
import time
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

_log = get_logger("cache")


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


class RedisCache:
    """Redis-backed cache that degrades to 'always miss' when Redis is unreachable (the DB stays the source of truth)."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._r = redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._r.get(key)
        except Exception as exc:  # noqa: BLE001
            _log.warning("cache_unavailable", op="get", error_type=type(exc).__name__)
            return None
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        try:
            await self._r.set(key, json.dumps(value), ex=ttl)
        except Exception as exc:  # noqa: BLE001
            _log.warning("cache_unavailable", op="set", error_type=type(exc).__name__)

    async def delete(self, key: str) -> None:
        try:
            await self._r.delete(key)
        except Exception as exc:  # noqa: BLE001
            _log.warning("cache_unavailable", op="delete", error_type=type(exc).__name__)


_cache: MemoryCache | RedisCache | None = None


def get_cache() -> MemoryCache | RedisCache:
    global _cache
    if _cache is None:
        url = get_settings().redis_url
        _cache = RedisCache(url) if url else MemoryCache()
    return _cache
