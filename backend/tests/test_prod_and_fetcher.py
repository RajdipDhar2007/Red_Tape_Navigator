import httpx
import pytest
from cryptography.fernet import Fernet

from app.core.config import Settings, get_settings, production_problems
from app.scraping import fetcher
from app.scraping.allowlist import DomainNotAllowed
from app.scraping.fetcher import HumanHandoffRequired, RobotsDisallowed, fetch_page

GOOD = dict(
    app_env="prod",
    secret_key="x" * 40,
    field_encryption_key=Fernet.generate_key().decode(),
    database_url="postgresql+asyncpg://u:p@db/rtn",
    cors_origins="https://app.example.in",
    demo_mode=False,
    grievance_contact="dpo@example.in",
    web_base_url="https://app.example.in",
    smtp_host="smtp.example.in",
    smtp_from="no-reply@example.in",
)


def test_good_prod_config_has_no_problems():
    assert production_problems(Settings(**GOOD)) == []


@pytest.mark.parametrize(
    ("override", "fragment"),
    [
        ({"secret_key": "dev-only-secret-key-change-me-0123456789"}, "SECRET_KEY"),
        ({"secret_key": "short"}, "SECRET_KEY"),
        ({"field_encryption_key": ""}, "FIELD_ENCRYPTION_KEY"),
        ({"database_url": "sqlite+aiosqlite:///./x.db"}, "PostgreSQL"),
        ({"cors_origins": "http://localhost:3000"}, "localhost"),
        ({"cors_origins": "http://app.example.in"}, "https"),
        ({"demo_mode": True}, "DEMO_MODE"),
        ({"grievance_contact": ""}, "GRIEVANCE_CONTACT"),
    ],
)
def test_each_unsafe_prod_setting_is_reported(override, fragment):
    problems = production_problems(Settings(**{**GOOD, **override}))
    assert any(fragment in p for p in problems)


def test_prod_startup_refuses_unsafe_config(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("DEMO_MODE", "true")
    try:
        with pytest.raises(RuntimeError, match="Unsafe production configuration"):
            get_settings()
    finally:
        get_settings.cache_clear()


def _client(routes: dict[str, httpx.Response]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return routes.get(str(request.url), httpx.Response(404))

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _reset_fetcher_state():
    for d in (fetcher._robots, fetcher._robots_at, fetcher._breakers, fetcher._last_hit):
        d.clear()
    yield


ARTICLE = "<html><body><article>" + "GST registration is free of charge for new taxpayers. " * 20 + "</article></body></html>"


async def test_fetch_ok_returns_sanitized_page():
    c = _client({"https://gst.gov.in/robots.txt": httpx.Response(404), "https://gst.gov.in/p": httpx.Response(200, text=ARTICLE)})
    page = await fetch_page("https://gst.gov.in/p", client=c)
    assert "GST registration" in page.text and page.content_hash and not page.injection_suspected


async def test_non_allowlisted_domain_is_rejected():
    with pytest.raises(DomainNotAllowed):
        await fetch_page("https://evil.example.com/p", client=_client({}))


async def test_robots_disallow_is_honoured():
    c = _client({"https://gst.gov.in/robots.txt": httpx.Response(200, text="User-agent: *\nDisallow: /")})
    with pytest.raises(RobotsDisallowed):
        await fetch_page("https://gst.gov.in/p", client=c)


async def test_captcha_wall_hands_over_to_human():
    wall = "<html><body>Please complete the reCAPTCHA to continue</body></html>"
    c = _client({"https://gst.gov.in/robots.txt": httpx.Response(404), "https://gst.gov.in/p": httpx.Response(200, text=wall)})
    with pytest.raises(HumanHandoffRequired):
        await fetch_page("https://gst.gov.in/p", client=c)


async def test_redirect_to_disallowed_host_is_blocked():
    c = _client({
        "https://gst.gov.in/robots.txt": httpx.Response(404),
        "https://gst.gov.in/p": httpx.Response(302, headers={"location": "https://evil.example.com/x"}),
    })
    with pytest.raises(DomainNotAllowed):
        await fetch_page("https://gst.gov.in/p", client=c)


async def test_robots_cache_expires(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            calls["n"] += 1
            return httpx.Response(404)
        return httpx.Response(200, text=ARTICLE)

    c = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await fetch_page("https://gst.gov.in/p", client=c)
    await fetch_page("https://gst.gov.in/p", client=c)
    assert calls["n"] == 1  # cached
    monkeypatch.setattr(fetcher, "_ROBOTS_TTL_SECONDS", -1)
    await fetch_page("https://gst.gov.in/p", client=c)
    assert calls["n"] == 2  # expired -> re-read


def test_prod_requires_smtp_and_https_web_url():
    base = {**GOOD, "web_base_url": "https://app.example.in", "smtp_host": "smtp.example.in", "smtp_from": "no-reply@example.in"}
    assert production_problems(Settings(**base)) == []
    assert any("SMTP" in p for p in production_problems(Settings(**{**base, "smtp_host": ""})))
    assert any("WEB_BASE_URL" in p for p in production_problems(Settings(**{**base, "web_base_url": "http://x"})))


def test_managed_postgres_urls_get_the_asyncpg_driver():
    from app.core.config import Settings

    assert Settings(database_url="postgres://u:p@h/db").database_url == "postgresql+asyncpg://u:p@h/db"
    assert Settings(database_url="postgresql://u:p@h/db").database_url == "postgresql+asyncpg://u:p@h/db"
    assert Settings(database_url="postgresql+asyncpg://u:p@h/db").database_url == "postgresql+asyncpg://u:p@h/db"
    assert Settings(database_url="sqlite+aiosqlite:///x.db").database_url.startswith("sqlite")
