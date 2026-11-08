"""Translate JSON responses of /sessions/* into the interface language (Accept-Language: hi | bn).

Plans and rules are stored in English; this turns them into Hindi or Bengali on the way out, so switching the language
takes effect immediately without redoing the research. Strings the tables do not know stay English. Files, images and
error pages are untouched.
"""
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.i18n_content import localize_json, pick_language


class LocalizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        lang = pick_language(request.headers.get("accept-language"))
        if lang == "en" or not request.url.path.startswith("/sessions") or "application/json" not in response.headers.get("content-type", ""):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            payload = json.dumps(localize_json(json.loads(body), lang), ensure_ascii=False).encode()
        except ValueError:  # not JSON after all: pass it through unchanged
            payload = body
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        headers["Vary"] = "Accept-Language"
        return Response(payload, status_code=response.status_code, headers=headers, media_type="application/json")
