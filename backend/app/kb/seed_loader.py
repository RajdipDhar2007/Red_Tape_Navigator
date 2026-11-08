"""Builds the seed rules pack from the catalogue and loads it into the KB.  Run: python -m app.kb.seed_loader"""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.kb import confidence as conf
from app.kb.catalog import CITIES, LICENCES, REQUIRED_OVERRIDES
from app.kb.store import ClaimDraft, now, upsert_claim
from app.scraping.sanitizer import content_hash


def _draft(key, cat, text, data, url, base, ts) -> ClaimDraft:
    return ClaimDraft(
        key=key, category=cat, text=text, data=data, source_url=url, fetched_at=ts,
        content_hash=content_hash(text),
        confidence=conf.score(base=base, official_domain=True, verified_live=False, seed=True),
        seed=True,
    )


def seed_drafts() -> list[ClaimDraft]:
    ts = now()
    out: list[ClaimDraft] = []
    for lid, lic in LICENCES.items():
        scopes: list[tuple[str, str | None, str | None]]
        if lid in REQUIRED_OVERRIDES:
            a_key, u_key = REQUIRED_OVERRIDES[lid]
            scopes = [(c, city[a_key], city[u_key]) for c, city in CITIES.items()]
        else:
            scopes = [("national", lic["authority"], lic["url"])]
        for scope, authority, url in scopes:
            p = f"{lid}:{scope}"
            where = "" if scope == "national" else f" in {CITIES[scope]['label']}"
            name = lic["name"]
            city_fee = lic.get("fee_by_city", {}).get(scope)
            fee = city_fee or lic["fee"]
            fee_conf = lic["fee_by_city_conf"] if city_fee else lic["fee_conf"]
            out += [
                _draft(f"{p}:requirement", "requirement", f"{name}{where}: {lic['why']}", {"licence": lid, "value": lic["why"]}, url, 0.75, ts),
                _draft(f"{p}:authority", "authority", f"Issuing authority for {name}{where}: {authority}", {"licence": lid, "value": authority}, url, 0.9 if scope == "national" else 0.8, ts),
                _draft(f"{p}:fee", "fee", f"Fee for {name}{where}: {fee}", {"licence": lid, "value": fee}, url, fee_conf, ts),
                _draft(f"{p}:timeline", "timeline", f"Expected timeline for {name}{where}: {lic['timeline']}", {"licence": lid, "value": lic["timeline"]}, url, lic["timeline_conf"], ts),
                _draft(f"{p}:documents", "documents", f"Documents for {name}{where}: " + "; ".join(lic["documents"]), {"licence": lid, "value": lic["documents"]}, url, 0.7, ts),
                _draft(f"{p}:form_link", "form_link", f"Apply for {name}{where} on the official portal: {url}", {"licence": lid, "value": url}, url, 0.85, ts),
            ]
    return out


async def seed_all(db: AsyncSession) -> dict[str, int]:
    stats = {"new": 0, "unchanged": 0, "changed": 0}
    for d in seed_drafts():
        _, status = await upsert_claim(db, d)
        stats[status] += 1
    return stats


async def _main() -> None:  # pragma: no cover
    from app.db.models import Base
    from app.db.session import get_engine, maker

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with maker()() as db:
        print(await seed_all(db))


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_main())
