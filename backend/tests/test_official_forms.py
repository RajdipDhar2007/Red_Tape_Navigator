from functools import cache

import httpx
import pymupdf
import pytest
from sqlalchemy import select

from app.db.models import ReviewItem, User
from app.db.session import maker
from app.forms import official
from app.forms.registry import TEMPLATE_DIR, get_template
from app.scraping import fetcher
from app.scraping.allowlist import DomainNotAllowed
from app.scraping.fetcher import HumanHandoffRequired, NotAPdf, fetch_pdf

URL = "https://foscos.fssai.gov.in/forms/form-a.pdf"
LOGIN = {"email": "a@example.com", "password": "correct-horse-battery"}


@cache
def _official_pdf(extra: str = "") -> bytes:
    """A stand-in for the department's PDF: same AcroForm fields as our template, different bytes per `extra`."""
    doc = pymupdf.open(str(TEMPLATE_DIR / "fssai_form_a.pdf"))
    if extra:
        doc[0].insert_text((20, 20), extra)
    out = doc.tobytes()
    doc.close()
    return out


@cache
def _blank_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    out = doc.tobytes()
    doc.close()
    return out


def _client(body: bytes | None, *, ctype: str = "application/pdf", status: int = 200, headers: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(status, content=body or b"", headers={"content-type": ctype, **(headers or {})})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _fetcher_for(body: bytes | None, **kw):
    async def f(url, **_):
        return await fetch_pdf(url, client=_client(body, **kw))

    return f


@pytest.fixture(autouse=True)
def _reset():
    for d in (fetcher._robots, fetcher._robots_at, fetcher._breakers, fetcher._last_hit):
        d.clear()
    yield


async def test_fetch_pdf_guard_rails():
    ok = await fetch_pdf(URL, client=_client(_official_pdf()))
    assert ok.content.startswith(b"%PDF-") and len(ok.sha256) == 64
    with pytest.raises(DomainNotAllowed):
        await fetch_pdf("https://evil.example.com/a.pdf", client=_client(_official_pdf()))
    with pytest.raises(NotAPdf):
        await fetch_pdf(URL, client=_client(b"<html>Not found</html>", ctype="text/html"))
    with pytest.raises(HumanHandoffRequired):
        await fetch_pdf(URL, client=_client(b"<html>Please complete the reCAPTCHA</html>", ctype="text/html"))
    with pytest.raises(ValueError, match="too large"):
        await fetch_pdf(URL, max_bytes=100, client=_client(_official_pdf()))
    with pytest.raises(DomainNotAllowed):  # a redirect off the allowlist is blocked at the hop
        await fetch_pdf(URL, client=_client(b"", status=302, headers={"location": "https://evil.example.com/x.pdf"}))


def test_compat_report_matches_field_map():
    t = get_template("fssai_form_a")
    good = official.compat_report(t, _official_pdf())
    assert good["compatible"] and not good["missing_required"] and good["matched"] > 5
    blank = official.compat_report(t, _blank_pdf())
    assert not blank["compatible"] and "no fillable fields" in blank["reason"]
    assert not official.compat_report(t, b"%PDF-1.4 garbage")["compatible"]


async def test_candidate_must_be_approved_before_citizens_get_it(client):
    async with maker()() as db:
        src, new = await official.fetch_candidate(db, "fssai_form_a", URL, fetcher=_fetcher_for(_official_pdf()))
        assert new and src.status == "candidate" and src.compatible
        assert await official.active_source(db, "fssai_form_a") is None  # not used until a human decides
        again, new2 = await official.fetch_candidate(db, "fssai_form_a", URL, fetcher=_fetcher_for(_official_pdf()))
        assert not new2 and again.id == src.id  # identical bytes: no duplicate
        done = await official.decide(db, src.id, activate=True, actor="officer")
        assert done.status == "active" and done.decided_by == "officer"
        active = await official.active_source(db, "fssai_form_a")
        assert active is not None and active.id == src.id


async def test_incompatible_pdf_cannot_be_activated(client):
    async with maker()() as db:
        src, _ = await official.fetch_candidate(db, "fssai_form_a", URL, fetcher=_fetcher_for(_blank_pdf()))
        assert not src.compatible
        with pytest.raises(official.FormSourceError, match="field map"):
            await official.decide(db, src.id, activate=True, actor="officer")
        assert (await official.decide(db, src.id, activate=False, actor="officer")).status == "rejected"


async def test_missing_url_is_a_clear_error(client):
    async with maker()() as db:
        with pytest.raises(official.FormSourceError, match="no official URL"):
            await official.fetch_candidate(db, "fssai_form_a", None, fetcher=_fetcher_for(_official_pdf()))


async def test_changed_form_becomes_candidate_and_old_copy_keeps_serving(client):
    async with maker()() as db:
        v1, _ = await official.fetch_candidate(db, "fssai_form_a", URL, fetcher=_fetcher_for(_official_pdf("v1")))
        await official.decide(db, v1.id, activate=True, actor="officer")
        report = await official.check_for_changes(db, fetcher=_fetcher_for(_official_pdf("v2 revised by department")))
        assert report["changed"] == ["fssai_form_a"] and report["checked"] == 1
        active = await official.active_source(db, "fssai_form_a")
        assert active is not None and active.id == v1.id  # still the approved one
        items = (await db.execute(select(ReviewItem).where(ReviewItem.reason.like("Official form changed%")))).scalars().all()
        assert len(items) == 1
        same = await official.check_for_changes(db, fetcher=_fetcher_for(_official_pdf("v1")))
        assert same["changed"] == [] and same["unchanged"] == 1
        broken = await official.check_for_changes(db, fetcher=_fetcher_for(None, status=500))
        assert broken["errors"] and broken["errors"][0]["form"] == "fssai_form_a"


async def test_admin_api_flow(client, auth, monkeypatch):
    headers, _ = auth
    # a citizen cannot fetch or approve anything
    assert (await client.post("/admin/forms/fssai_form_a/fetch", json={"url": URL}, headers=headers)).status_code == 403
    assert (await client.get("/admin/forms", headers=headers)).status_code == 403
    async with maker()() as db:
        u = (await db.execute(User.__table__.select())).first()
        user = await db.get(User, u.id)
        assert user is not None
        user.role = "admin"
        await db.commit()
    ah = {"Authorization": f"Bearer {(await client.post('/auth/login', json=LOGIN)).json()['access_token']}"}

    async def fake(url, **_):
        return await fetch_pdf(url, client=_client(_official_pdf("official copy")))

    monkeypatch.setattr(official, "fetch_pdf", fake)
    listing = (await client.get("/admin/forms", headers=ah)).json()
    assert {f["form_id"] for f in listing} >= {"fssai_form_a", "trade_licence", "udyam_details"}
    assert all(f["serving"] == "placeholder" for f in listing)

    assert (await client.post("/admin/forms/nope/fetch", json={}, headers=ah)).status_code == 404
    assert (await client.post("/admin/forms/fssai_form_a/fetch", json={}, headers=ah)).status_code == 422  # no URL known
    bad = await client.post("/admin/forms/fssai_form_a/fetch", json={"url": "https://evil.example.com/a.pdf"}, headers=ah)
    assert bad.status_code == 422
    fetched = await client.post("/admin/forms/fssai_form_a/fetch", json={"url": URL}, headers=ah)
    assert fetched.status_code == 200 and fetched.json()["new"] and fetched.json()["compatible"]
    sid = fetched.json()["id"]
    pdf = await client.get(f"/admin/forms/sources/{sid}/pdf", headers=ah)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert (await client.post(f"/admin/forms/sources/{sid}/bogus", headers=ah)).status_code == 404
    assert (await client.post(f"/admin/forms/sources/{sid}/activate", headers=ah)).json()["status"] == "active"
    assert (await client.post(f"/admin/forms/sources/{sid}/reject", headers=ah)).status_code == 409  # cannot reject the live copy
    serving = [f for f in (await client.get("/admin/forms", headers=ah)).json() if f["form_id"] == "fssai_form_a"][0]["serving"]
    assert serving == "official"
    assert (await client.post("/admin/forms/refresh", headers=ah)).json()["checked"] == 1


async def test_citizen_review_and_download_use_the_approved_official_copy(client, auth):
    from tests.test_api_flow import ANSWERS, start

    headers, s = await start(client, auth)
    sid = s["id"]
    await client.post(f"/sessions/{sid}/research", json={}, headers=headers)
    for _ in range(40):
        st = (await client.get(f"/sessions/{sid}/interview", headers=headers)).json()
        if not st["questions"]:
            break
        keys = [q["key"] for q in st["questions"]]
        await client.post(f"/sessions/{sid}/interview", json={"answers": {k: ANSWERS[k] for k in keys}}, headers=headers)

    before = {f["form_id"]: f for f in (await client.get(f"/sessions/{sid}/review", headers=headers)).json()["forms"]}
    assert before["fssai_form_a"]["placeholder"] and before["fssai_form_a"]["official_source"] is None

    marker = "OFFICIAL-COPY-MARKER"
    async with maker()() as db:
        src, _ = await official.fetch_candidate(db, "fssai_form_a", URL, fetcher=_fetcher_for(_official_pdf(marker)))
        await official.decide(db, src.id, activate=True, actor="officer")

    after = {f["form_id"]: f for f in (await client.get(f"/sessions/{sid}/review", headers=headers)).json()["forms"]}
    f = after["fssai_form_a"]
    assert not f["placeholder"] and "PLACEHOLDER" not in f["title"]
    assert f["official_source"]["url"] == URL and f["official_source"]["sha256"] == src.sha256
    assert after["trade_licence"]["placeholder"] and after["udyam_details"]["placeholder"]  # others unaffected

    assert (await client.post(f"/sessions/{sid}/review", json={"confirm": True}, headers=headers)).status_code == 200
    pdf = (await client.get(f"/sessions/{sid}/forms/fssai_form_a/download", headers=headers)).content
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    assert marker in doc[0].get_text()  # the file the citizen downloads is the approved official PDF
    values = {w.field_name: w.field_value for p in doc for w in p.widgets()}
    assert values["applicant_name"] == ANSWERS["applicant_name"]
