"""Dependency-free hashing embedding (feature hashing, L2-normalised).

Good enough for small-KB retrieval and works without an embedding API. On PostgreSQL the same vectors can be
stored in a pgvector column (see Alembic migration) and queried with `<=>`; in SQLite/tests we compute cosine in
Python. Swap `embed` for a real model without changing callers.
"""
import hashlib
import math
import re

DIM = 256
_TOKEN = re.compile(r"\w+", re.U)


def embed(text: str) -> list[float]:
    v = [0.0] * DIM
    for tok in _TOKEN.findall(text.lower()):
        h = int(hashlib.md5(tok.encode(), usedforsecurity=False).hexdigest(), 16)  # noqa: S324
        v[h % DIM] += 1.0 if (h >> 8) & 1 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))
