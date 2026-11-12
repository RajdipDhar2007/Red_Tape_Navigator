"""Arq worker: scheduled KB refresh (diff detection), retention purge, reminder dispatch.

Run: arq app.jobs.worker.WorkerSettings
"""
from collections.abc import Awaitable, Callable
from typing import TypeVar

from arq import cron
from arq.connections import RedisSettings

from app.agent.llm import LLM
from app.agent.research import refresh_all
from app.core.config import get_settings
from app.core.errors import capture_exception
from app.core.logging import get_logger
from app.db.session import maker
from app.followup.reminders import dispatch_due
from app.integrations.factory import get_integrations
from app.services.privacy import purge_expired

_log = get_logger("worker")
T = TypeVar("T")


async def _run_observed(job_name: str, coro_fn: Callable[[], Awaitable[T]]) -> T:
    _log.info("worker_job_started", job=job_name)
    try:
        res = await coro_fn()
        _log.info("worker_job_completed", job=job_name)
        return res
    except Exception as exc:
        capture_exception(exc, job=job_name)
        raise


async def refresh_rules(ctx) -> dict:
    async def _do() -> dict:
        async with maker()() as db:
            return await refresh_all(db, llm=LLM())

    return await _run_observed("refresh_rules", _do)


async def forms_job(ctx) -> dict:
    """Re-fetch official form PDFs; a changed file becomes a candidate + officer review item (never auto-activated)."""
    from app.forms.official import check_for_changes

    async def _do() -> dict:
        async with maker()() as db:
            return await check_for_changes(db)

    return await _run_observed("forms_job", _do)


async def purge_job(ctx) -> int:
    async def _do() -> int:
        async with maker()() as db:
            return await purge_expired(db)

    return await _run_observed("purge_job", _do)


async def reminders_job(ctx) -> int:
    async def _do() -> int:
        async with maker()() as db:
            return await dispatch_due(db, get_integrations())

    return await _run_observed("reminders_job", _do)


class WorkerSettings:
    functions = [refresh_rules, forms_job, purge_job, reminders_job]
    cron_jobs = [
        cron(refresh_rules, weekday={0}, hour={2}, minute={0}),  # weekly, Monday 02:00
        cron(forms_job, weekday={0}, hour={2}, minute={30}),  # weekly, after the rules refresh
        cron(purge_job, hour={3}, minute={0}),  # daily
        cron(reminders_job, minute={0, 30}),  # every 30 minutes
    ]
    health_check_interval = 30  # seconds; used by `arq --check` (compose healthcheck)
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url or "redis://localhost:6379/0")
