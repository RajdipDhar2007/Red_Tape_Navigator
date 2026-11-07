"""Polite fetcher: allowlist + robots.txt + per-domain rate limit + retry/circuit breaker.

Static pages use httpx + trafilatura. JS-heavy portals use Playwright (`render_js=True`).
Captcha / login walls are never bypassed: they raise HumanHandoffRequired.
"""
import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib import robotparser
from urllib.parse import urlparse

import httpx
import trafilatura

from app.core.metrics import SCRAPES
from app.core.resilience import CircuitBreaker, call_with_resilience
from app.core.tracing import span
from app.scraping.allowlist import assert_allowed, load_sources
from app.scraping.sanitizer import content_hash, sanitize


class HumanHandoffRequired(RuntimeError):
    """Raised on captcha/login walls. The UI shows a manual handoff step instead."""


class RobotsDisallowed(RuntimeError):
    pass


@dataclass
class Page:
    url: str
    text: str
    fetched_at: datetime
    content_hash: str
    injection_suspected: bool


_WALL_MARKERS = ("captcha", "recaptcha", "please log in", "login to continue", "sign in to continue")
_breakers: dict[str, CircuitBreaker] = {}
_last_hit: dict[str, list[float]] = {}
_robots: dict[str, robotparser.RobotFileParser | None] = {}


def _breaker(host: str) -> CircuitBreaker:
    return _breakers.setdefault(host, CircuitBreaker(failure_threshold=3, reset_seconds=60))


async def _throttle(host: str, per_minute: int) -> None:
    hits = [t for t in _last_hit.get(host, []) if time.monotonic() - t < 60]
    if len(hits) >= per_minute:
        await asyncio.sleep(max(0.0, 60 - (time.monotonic() - hits[0])))
    hits.append(time.monotonic())
    _last_hit[host] = hits


async def _robots_ok(client: httpx.AsyncClient, url: str, ua: str) -> bool:
    u = urlparse(url)
    root = f"{u.scheme}://{u.netloc}"
    if root not in _robots:
        rp = robotparser.RobotFileParser()
        try:
            r = await client.get(f"{root}/robots.txt", timeout=10)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
                _robots[root] = rp
            else:
                _robots[root] = None  # no robots file -> allowed
        except httpx.HTTPError:
            _robots[root] = None
    rp = _robots[root]
    return True if rp is None else rp.can_fetch(ua, url)


async def _render_js(url: str, ua: str) -> str:  # pragma: no cover - needs a browser
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(user_agent=ua)
        await page.goto(url, timeout=30000)
        html = await page.content()
        await browser.close()
        return html


async def fetch_page(url: str, *, render_js: bool = False, client: httpx.AsyncClient | None = None) -> Page:
    with span("scrape.fetch", host=urlparse(url).hostname or ""):
        try:
            page = await _fetch_page(url, render_js=render_js, client=client)
        except Exception as exc:
            SCRAPES.labels(type(exc).__name__).inc()
            raise
    SCRAPES.labels("ok").inc()
    return page


async def _fetch_page(url: str, *, render_js: bool = False, client: httpx.AsyncClient | None = None) -> Page:
    url = assert_allowed(url)
    cfg = load_sources()
    ua = cfg["user_agent"]
    host = urlparse(url).hostname or ""
    own = client is None
    client = client or httpx.AsyncClient(headers={"User-Agent": ua}, follow_redirects=False)
    try:
        if not await _robots_ok(client, url, ua):
            raise RobotsDisallowed(url)
        await _throttle(host, cfg["rate_limit_per_domain_per_minute"])

        async def go() -> str:
            if render_js:
                return await _render_js(url, ua)
            cur = url
            for _ in range(3):  # manual redirects so every hop is re-checked against the allowlist
                r = await client.get(cur, timeout=15)
                if r.is_redirect:
                    cur = assert_allowed(str(httpx.URL(cur).join(r.headers["location"])))
                    continue
                r.raise_for_status()
                if len(r.content) > cfg["max_bytes"]:
                    raise ValueError("response too large")
                return r.text
            raise ValueError("too many redirects")

        html = await call_with_resilience(
            go, breaker=_breaker(host), retries=2, timeout=35, retry_on=(httpx.HTTPError, ValueError)
        )
    finally:
        if own:
            await client.aclose()
    text = trafilatura.extract(html) or ""
    if any(m in html.lower() for m in _WALL_MARKERS) and len(text) < 500:
        raise HumanHandoffRequired(f"Captcha or login required at {url}; please complete this step manually.")
    clean, flagged = sanitize(text)
    return Page(
        url=url, text=clean, fetched_at=datetime.now(UTC), content_hash=content_hash(clean), injection_suspected=flagged
    )
