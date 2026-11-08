"""Translate backend response text into Hindi or Bengali.

The interface sends its language in ``Accept-Language``; ``localize_json`` then rewrites every string the tables know. Anything
the tables do not know stays English (never guessed). Official names (FSSAI, GST, PAN, Aadhaar...) stay in Latin letters.
Translations were written for clarity and are flagged for native-speaker review in docs/LAUNCH_CHECKLIST.md.
"""
import logging
import re
from functools import lru_cache
from typing import Any

from app.i18n_content import data_bn, data_hi
from app.i18n_content.source import SECTIONS, english_sources
from app.kb.catalog import CITIES, LICENCES

log = logging.getLogger(__name__)
LANGS = ("hi", "bn")
_DATA = {"hi": data_hi, "bn": data_bn}

# claim sentence templates: (english prefix pattern, key into data.TEMPLATES)
_CLAIM_PATTERNS = [
    (re.compile(r"^Issuing authority for (?P<x>.+?): (?P<v>.+)$", re.S), "authority"),
    (re.compile(r"^Fee for (?P<x>.+?): (?P<v>.+)$", re.S), "fee"),
    (re.compile(r"^Expected timeline for (?P<x>.+?): (?P<v>.+)$", re.S), "timeline"),
    (re.compile(r"^Documents for (?P<x>.+?): (?P<v>.+)$", re.S), "documents"),
    (re.compile(r"^Apply for (?P<x>.+?) on the official portal: (?P<v>https?://\S+)$", re.S), "form_link"),
]
_REQUIREMENT = re.compile(r"^(?P<x>.+?): (?P<v>.+)$", re.S)
_COULD_NOT_FORMAT = re.compile(r"^Could not format value \((?P<e>.*)\); left blank\.$", re.S)
_COMPLETE_FIRST = re.compile(r"^Complete first: (?P<v>.+)$", re.S)


def pick_language(accept_language: str | None) -> str:
    primary = (accept_language or "").split(",")[0].strip().lower().split("-")[0]
    return primary if primary in LANGS else "en"


@lru_cache(maxsize=4)
def _table(lang: str) -> dict[str, str]:
    """english -> translation, by zipping the ordered English sources with the aligned data lists (prefix-checked)."""
    data, src = _DATA[lang], english_sources()
    table: dict[str, str] = dict(data.FIXED)
    for section in SECTIONS:
        rows = getattr(data, section.upper())
        english = src[section]
        if len(rows) != len(english):
            log.error("translation table %s/%s has %d rows for %d English strings", lang, section, len(rows), len(english))
        for en, row in zip(english, rows, strict=False):
            prefix, text = row
            if en.startswith(prefix):
                table[en] = text
            else:
                log.error("translation table %s/%s misaligned at %r", lang, section, prefix)
    return table


@lru_cache(maxsize=4)
def _docs_by_length(lang: str) -> list[str]:
    return sorted((k for k in english_sources()["docs"] if k in _table(lang)), key=len, reverse=True)


def _city_name(lang: str, label: str) -> str | None:
    for c in CITIES.values():
        if c["label"] == label:
            return _DATA[lang].CITIES.get(label)
    return None


def _licence_name(lang: str, english: str) -> str | None:
    return _table(lang).get(english) if any(lic["name"] == english for lic in LICENCES.values()) else None


def _localize_subject(lang: str, x: str) -> str | None:
    """'Udyam (MSME) Registration' or 'Fire Safety NOC in Kolkata' -> localized, or None when x is not a licence (+ city)."""
    name, city = x, None
    if " in " in x:
        head, _, tail = x.rpartition(" in ")
        if _city_name(lang, tail):
            name, city = head, tail
    local = _licence_name(lang, name)
    if not local:
        return None
    return f"{local} ({_city_name(lang, city)})" if city else local


def _localize_documents(lang: str, rest: str) -> str:
    table, known, out = _table(lang), _docs_by_length(lang), []
    while rest:
        for item in known:
            if rest.startswith(item) and (len(rest) == len(item) or rest[len(item):].startswith("; ")):
                out.append(table[item])
                rest = rest[len(item) + 2:]
                break
        else:
            part, _, rest = rest.partition("; ")
            out.append(part)
    return "; ".join(out)


def localize_text(text: str, lang: str) -> str:
    if lang not in LANGS or not text or len(text) < 3:
        return text
    table = _table(lang)
    hit = table.get(text)
    if hit:
        return hit
    data = _DATA[lang]
    for pattern, key in _CLAIM_PATTERNS:
        m = pattern.match(text)
        if m:
            subject = _localize_subject(lang, m.group("x"))
            if subject:
                v = m.group("v")
                v = _localize_documents(lang, v) if key == "documents" else table.get(v, v)
                return data.TEMPLATES[key].format(x=subject, v=v)
    m = _REQUIREMENT.match(text)
    if m:
        subject = _localize_subject(lang, m.group("x"))
        if subject:
            v = m.group("v")
            return f"{subject}: {table.get(v, v)}"
    m = _COMPLETE_FIRST.match(text)
    if m:
        names = ", ".join(_licence_name(lang, n.strip()) or n.strip() for n in m.group("v").split(", "))
        return data.TEMPLATES["complete_first"].format(v=names)
    m = _COULD_NOT_FORMAT.match(text)
    if m:
        return data.TEMPLATES["could_not_format"].format(e=m.group("e"))
    return text


def localize_json(obj: Any, lang: str) -> Any:
    if lang not in LANGS:
        return obj
    if isinstance(obj, str):
        return localize_text(obj, lang)
    if isinstance(obj, list):
        return [localize_json(v, lang) for v in obj]
    if isinstance(obj, dict):
        return {k: localize_json(v, lang) for k, v in obj.items()}
    return obj


def detect_language(text: str) -> str:
    """Language of a stored text by script (reminder titles are stored in the citizen's language)."""
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    if re.search(r"[ঀ-৿]", text):
        return "bn"
    return "en"


def reminder_title(kind: str, licence_name: str, lang: str) -> str:
    """Reminder titles, built in the citizen's language at scheduling time."""
    en = {"status": f"Check status of your {licence_name} application",
          "renewal": f"Renewal check for {licence_name} (verify the exact due date on your certificate)"}[kind]
    if lang not in LANGS:
        return en
    name = _table(lang).get(licence_name, licence_name)
    return _DATA[lang].TEMPLATES[f"reminder_{kind}"].format(x=name)
