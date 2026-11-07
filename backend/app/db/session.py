from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine = None
_maker = None


def get_engine():
    global _engine, _maker
    if _engine is None:
        url = get_settings().database_url
        if url.startswith("sqlite") and "///./" in url:
            Path(url.split("///./")[1]).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(url, pool_pre_ping=not url.startswith("sqlite"))
        _maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def maker() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _maker is not None
    return _maker


async def get_db() -> AsyncIterator[AsyncSession]:
    async with maker()() as session:
        yield session


async def reset_engine() -> None:
    global _engine, _maker
    if _engine is not None:
        await _engine.dispose()
    _engine = _maker = None
