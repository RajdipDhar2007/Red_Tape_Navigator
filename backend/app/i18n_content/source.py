"""The ordered lists of English strings that the translation tables must cover.

Built from the catalogue and the form templates, so the tables in data_hi.py / data_bn.py cannot silently drift: tests compare
each table entry with the English string at the same position (and fail when a string is added without a translation).
"""
import glob
import json
import pathlib

from app.kb.catalog import CITIES, LICENCES

_TEMPLATES = pathlib.Path(__file__).resolve().parents[1] / "forms" / "templates"
SECTIONS = ("names", "prose", "docs", "authorities", "titles", "labels", "notes")


def english_sources() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {k: [] for k in SECTIONS}
    seen: set[str] = set()

    def add(section: str, text: str | None) -> None:
        if text and text not in seen:
            seen.add(text)
            out[section].append(text)

    for lic in LICENCES.values():
        add("names", lic["name"])
        for k in ("fee", "timeline", "why"):
            add("prose", lic[k])
        for d in lic["documents"]:
            add("docs", d)
        add("authorities", lic.get("authority"))
        for entry in (lic.get("by_city") or {}).values():
            for k in ("fee", "timeline", "why"):
                add("prose", entry.get(k))
            for d in entry.get("documents", []):
                add("docs", d)
            add("authorities", entry["authority"])
        for v in (lic.get("fee_by_city") or {}).values():
            add("prose", v)
    for c in CITIES.values():
        for k in ("authority", "fire_authority", "labour_authority", "pollution_authority"):
            add("authorities", c[k])
    for p in sorted(glob.glob(str(_TEMPLATES / "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        add("titles", d["title"])
        add("authorities", d["authority"])
        for w in d.get("warnings", []) or []:
            add("notes", w["message"])
        for f in d["fields"]:
            add("labels", f["label"])
            add("notes", f.get("note"))
    return out
