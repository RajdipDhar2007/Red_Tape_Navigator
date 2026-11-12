"""Security headers, request ids, body-size limit, rate limiting, metrics and tracing."""
import math
import time
import uuid
from collections import defaultdict, deque
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core import metrics
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.tracing import span

log = get_logger("http")
MAX_BODY = 1_000_000  # 1 MB: forms are small; blocks abuse
DEFAULT_MAX_RATE_LIMIT_KEYS = 10_000

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class RateLimiter:
    """Rate limiter backed by Redis when REDIS_URL is configured, with a bounded in-memory sliding-window fallback."""

    def __init__(
        self,
        max_keys: int = DEFAULT_MAX_RATE_LIMIT_KEYS,
        redis_url: str | None = None,
        redis_client: Any | None = None,
    ) -> None:
        self.max_keys = max(1, max_keys)
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_sweep: float = 0.0
        self._configured_redis_url = redis_url
        self._redis: Any | None = redis_client
        self._redis_url: str = redis_url or ""

    def _evict_expired(self, now: float, window: float) -> None:
        cutoff = now - window
        for k, q in list(self.hits.items()):
            while q and q[0] <= cutoff:
                q.popleft()
            if not q:
                self.hits.pop(k, None)
        self._last_sweep = now

    def allow(self, key: str, limit: int, window: float = 60.0, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if not self.hits:
            self._last_sweep = now
        elif (
            now - self._last_sweep >= window
            or now < self._last_sweep
            or len(self.hits) >= self.max_keys
        ):
            self._evict_expired(now, window)

        cutoff = now - window
        q = self.hits.get(key)
        if q is not None:
            while q and q[0] <= cutoff:
                q.popleft()
            if not q:
                self.hits.pop(key, None)
                q = None

        if q is not None and len(q) >= limit:
            return False
        if limit <= 0:
            return False

        if q is None:
            while len(self.hits) >= self.max_keys:
                oldest_key = next(iter(self.hits))
                self.hits.pop(oldest_key, None)
            q = self.hits[key]
        else:
            # Refresh insertion order so active keys are kept and oldest idle keys are evicted first
            self.hits.pop(key, None)
            self.hits[key] = q

        q.append(now)
        return True

    def _get_redis(self) -> Any | None:
        if self._redis is not None and self._configured_redis_url is None and not self._redis_url:
            return self._redis
        url = self._configured_redis_url if self._configured_redis_url is not None else get_settings().redis_url
        if not url:
            return None
        if self._redis is None or self._redis_url != url:
            import redis.asyncio as redis

            self._redis = redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
            self._redis_url = url
        return self._redis

    async def allow_async(self, key: str, limit: int, window: float = 60.0, now: float | None = None) -> bool:
        if limit <= 0:
            return False
        client = self._get_redis()
        if client is not None:
            ts = time.time() if now is None else now
            bucket = int(ts // window)
            rkey = f"rtn:rl:{key}:{bucket}"
            ttl = max(1, int(math.ceil(window)) + 1)
            try:
                pipe = client.pipeline(transaction=True)
                pipe.incr(rkey)
                pipe.expire(rkey, ttl)
                res = await pipe.execute()
                return int(res[0]) <= limit
            except Exception as exc:  # noqa: BLE001
                log.warning("rate_limiter_redis_unavailable", error_type=type(exc).__name__)
        return self.allow(key, limit, window=window, now=now)


limiter = RateLimiter()


def _client_ip(request: Request) -> str:
    # Behind a trusted proxy set the first X-Forwarded-For hop; otherwise use the socket peer.
    fwd = request.headers.get("x-forwarded-for")
    if fwd and get_settings().trust_proxy:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class HardeningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex
        s = get_settings()
        path = request.url.path
        start = time.perf_counter()

        max_body = max(MAX_BODY, s.max_upload_bytes + 65_536) if path.startswith("/documents") and request.method == "POST" else MAX_BODY
        if int(request.headers.get("content-length") or 0) > max_body:
            resp: Response = JSONResponse({"detail": "Request too large"}, status_code=413)
        else:
            ip = _client_ip(request)
            auth_path = path.startswith("/auth")
            limit = s.auth_rate_limit_per_minute if auth_path else s.rate_limit_per_minute
            if path not in ("/health", "/ready") and not await limiter.allow_async(
                f"{ip}:{'auth' if auth_path else 'api'}", limit
            ):
                metrics.RATE_LIMITED.inc()
                resp = JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})
            else:
                with span("http.request", method=request.method) as sp:
                    resp = await call_next(request)
                    route = getattr(request.scope.get("route"), "path", "unmatched")
                    sp.set_attribute("http.route", route)
                    sp.set_attribute("http.status_code", resp.status_code)

        route = getattr(request.scope.get("route"), "path", "unmatched")
        dur = time.perf_counter() - start
        metrics.HTTP_REQUESTS.labels(request.method, route, str(resp.status_code)).inc()
        metrics.HTTP_LATENCY.labels(route).observe(dur)
        for k, v in SECURITY_HEADERS.items():
            resp.headers.setdefault(k, v)
        resp.headers["X-Request-ID"] = rid
        if not path.startswith("/metrics"):
            resp.headers.setdefault("Cache-Control", "no-store")
        # never log query strings, bodies or headers (may contain PII/tokens)
        log.info("request", request_id=rid, method=request.method, route=route, status=resp.status_code, ms=round(dur * 1000, 1))
        return resp
