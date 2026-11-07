"""Versioned rules knowledge base. Every claim carries source URL, fetch timestamp and content hash."""
import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Claim
from app.kb import confidence as conf
from app.kb.embedding import cosine, embed
from app.scraping.allowlist import is_allowed

CATEGORIES = ("requirement", "authority", "fee", "timeline", "documents", "form_link")


class ClaimDraft(BaseModel):
    """Validated claim. Construction fails without a citation or from a non-allowlisted source."""

    key: str
    category: str
    text: str = Field(min_length=3)
    data: dict = Field(default_factory=dict)
    source_url: str
    fetched_at: datetime
    content_hash: str = Field(min_length=16)
    confidence: float = Field(ge=0, le=1)
    seed: bool = False

    @field_validator("source_url")
    @classmethod
    def _official(cls, v: str) -> str:
        if not is_allowed(v):
            raise ValueError(f"source not on official allowlist: {v}")
        return v

    @field_validator("category")
    @classmethod
    def _cat(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError("unknown category")
        return v


UpsertStatus = Literal["new", "unchanged", "changed"]


async def upsert_claim(db: AsyncSession, d: ClaimDraft) -> tuple[Claim, UpsertStatus]:
    cur = (
        await db.execute(select(Claim).where(Claim.key == d.key, Claim.current.is_(True)))
    ).scalar_one_or_none()
    if cur and cur.content_hash == d.content_hash:
        cur.fetched_at = d.fetched_at
        cur.confidence = max(cur.confidence, d.confidence) if not d.seed else cur.confidence
        cur.needs_verification = conf.needs_verification(cur.confidence)
        await db.commit()
        return cur, "unchanged"
    row = Claim(
        key=d.key, category=d.category, text=d.text, data=d.data, source_url=d.source_url,
        fetched_at=d.fetched_at, content_hash=d.content_hash, confidence=d.confidence,
        needs_verification=conf.needs_verification(d.confidence), seed=d.seed, embedding=embed(d.text),
    )
    status: UpsertStatus = "new"
    if cur:
        cur.current = False
        row.version = cur.version + 1
        row.changed_from = cur.id
        status = "changed"
    db.add(row)
    await db.commit()
    return row, status


async def get_current(db: AsyncSession, key: str) -> Claim | None:
    return (await db.execute(select(Claim).where(Claim.key == key, Claim.current.is_(True)))).scalar_one_or_none()


async def claims_for_prefixes(db: AsyncSession, prefixes: list[str]) -> list[Claim]:
    rows = (await db.execute(select(Claim).where(Claim.current.is_(True)))).scalars().all()
    return [c for c in rows if any(c.key.startswith(p) for p in prefixes)]


async def search(db: AsyncSession, query: str, k: int = 5) -> list[tuple[Claim, float]]:
    q = embed(query)
    if db.get_bind().dialect.name == "postgresql":  # pragma: no cover - exercised in CI against pgvector
        stmt = select(Claim).where(Claim.current.is_(True), Claim.embedding.is_not(None)).order_by(Claim.embedding.cosine_distance(q)).limit(50)
        rows = (await db.execute(stmt)).scalars().all()
    else:
        rows = (await db.execute(select(Claim).where(Claim.current.is_(True)))).scalars().all()
    qtok = set(re.findall(r"\w+", query.lower()))

    def lexical(c: Claim) -> float:  # hybrid search: embedding cosine + keyword overlap
        ctok = set(re.findall(r"\w+", (c.key + " " + c.text).lower()))
        return len(qtok & ctok) / (len(qtok) or 1)

    scored = [(c, cosine(q, c.embedding) + lexical(c)) for c in rows if c.embedding]
    return sorted(scored, key=lambda t: t[1], reverse=True)[:k]


def now() -> datetime:
    return datetime.now(UTC)
