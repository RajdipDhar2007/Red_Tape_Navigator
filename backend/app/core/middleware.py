"""Security headers, request ids, body-size limit, rate limiting, metrics and tracing."""
import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core import metrics
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.tracing import span

log = get_logger("http")
MAX_BODY = 1_000_000  # 1 MB: forms are small; blocks abuse

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
    """Sliding-window limiter. In-process; use a Redis-backed limiter (e.g. at the gateway) for multi-replica."""

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window: float = 60.0, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        q = self.hits[key]
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


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

        if int(request.headers.get("content-length") or 0) > MAX_BODY:
            resp: Response = JSONResponse({"detail": "Request too large"}, status_code=413)
        else:
            ip = _client_ip(request)
            auth_path = path.startswith("/auth")
            limit = s.auth_rate_limit_per_minute if auth_path else s.rate_limit_per_minute
            if path not in ("/health", "/ready") and not limiter.allow(f"{ip}:{'auth' if auth_path else 'api'}", limit):
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
