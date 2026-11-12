"""Checks a LIVE deployment from the outside. Run it after every production deploy.

  python scripts/verify_deploy.py https://<api-host> https://<web-host>            # read-only checks
  python scripts/verify_deploy.py https://<api-host> https://<web-host> --journey  # also signs up a throwaway
                                                                                    # account, builds a plan, then erases it

Exit code 0 means every check passed. It never needs a secret, and with --journey it deletes what it creates.
Uses only httpx (already a backend dependency).
"""
import sys
import uuid

import httpx

FAILED: list[str] = []


def check(ok: bool, what: str, detail: str = "") -> bool:
    print(f"{'ok  ' if ok else 'FAIL'} {what}{'' if ok or not detail else ': ' + detail}")
    if not ok:
        FAILED.append(what)
    return ok


def api_checks(c: httpx.Client, web: str) -> None:
    r = c.get("/health")
    check(r.status_code == 200, "API /health answers 200", str(r.status_code))
    r = c.get("/ready")
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    check(r.status_code == 200 and body.get("database") is True, "API /ready: database reachable", r.text[:120])
    check(body.get("kb_claims", 0) > 0, "rules are loaded", f"kb_claims={body.get('kb_claims')}")
    check(body.get("demo_mode") is False, "DEMO_MODE is off", f"demo_mode={body.get('demo_mode')}")
    h = {k.lower(): v for k, v in r.headers.items()}
    check("max-age" in h.get("strict-transport-security", ""), "API sends HSTS")
    check(h.get("x-content-type-options") == "nosniff", "API sends X-Content-Type-Options: nosniff")
    check(c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404, "API docs are not exposed in production")
    check(c.get("/sessions").status_code == 401, "private routes refuse anonymous callers")
    check(c.get("/metrics").status_code == 401, "/metrics needs its token")
    pol = c.get("/privacy/policy").json()
    check("Not configured" not in str(pol.get("grievance_contact", "Not configured")), "grievance contact is configured")

    pre = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    good = c.options("/auth/login", headers={"Origin": web, **pre})
    check(good.headers.get("access-control-allow-origin") == web, "the website's origin is allowed by CORS",
          f"allow-origin={good.headers.get('access-control-allow-origin')!r}: set CORS_ORIGINS to {web}")
    bad = c.options("/auth/login", headers={"Origin": "https://evil.example", **pre})
    check(bad.headers.get("access-control-allow-origin") is None, "other origins are refused by CORS")


def web_checks(w: httpx.Client, api: str) -> None:
    for locale in ("en", "hi", "bn"):
        r = w.get(f"/{locale}")
        check(r.status_code == 200 and f'lang="{locale}"' in r.text, f"website /{locale} loads in the right language", str(r.status_code))
    r = w.get("/en")
    csp = r.headers.get("content-security-policy", "")
    check("frame-ancestors 'none'" in csp, "website sends a Content-Security-Policy")
    check(api in csp, "the website was built against this API", f"NEXT_PUBLIC_API_URL on the host must be {api}, then redeploy")
    check("localhost" not in csp, "no localhost left in the website build")
    for path in ("/en/privacy", "/en/terms", "/robots.txt", "/sitemap.xml", "/manifest.webmanifest"):
        check(w.get(path).status_code == 200, f"website {path} loads")
    check("Disallow: /en/account" in w.get("/robots.txt").text, "private pages are kept out of search engines")


def journey(c: httpx.Client) -> None:
    email, password = f"deploy-check-{uuid.uuid4().hex[:12]}@example.com", "Check-" + uuid.uuid4().hex
    r = c.post("/auth/register", json={"email": email, "password": password})
    if not check(r.status_code == 201, "a new account can sign up", f"{r.status_code} {r.text[:120]}"):
        return
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    try:
        check(c.post("/auth/login", json={"email": email, "password": password}).status_code == 200, "that account can log in")
        check(c.post("/consent", json={"purpose": "service", "granted": True}, headers=h).status_code == 201, "consent is recorded")
        s = c.post("/sessions", json={"goal": "I want to open a small bakery in Kolkata", "language": "en"}, headers=h)
        if check(s.status_code == 201, "a goal can be submitted", s.text[:120]):
            sid = s.json()["id"]
            res = c.post(f"/sessions/{sid}/research", json={}, headers=h)
            steps = res.json().get("plan", {}).get("steps", []) if res.status_code == 200 else []
            check(len(steps) > 0, "the plan lists licences with sources", f"{res.status_code} {res.text[:120]}")
            hi = c.get(f"/sessions/{sid}/checklist", headers={**h, "Accept-Language": "hi"})
            check(hi.status_code == 200, "the checklist loads in Hindi")
    finally:
        gone = c.delete("/privacy/me", headers=h)
        check(gone.status_code == 200, "the throwaway account was erased again", f"{gone.status_code}: erase {email} by hand")


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2 or not all(a.startswith("http") for a in args):
        print(__doc__)
        return 2
    api, web = (a.rstrip("/") for a in args)
    with httpx.Client(base_url=api, timeout=90) as c, httpx.Client(base_url=web, timeout=90, follow_redirects=True) as w:
        api_checks(c, web)
        web_checks(w, api)
        if "--journey" in argv:
            journey(c)
    print(f"\n{len(FAILED)} check(s) failed: {FAILED}" if FAILED else "\nAll checks passed.")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
