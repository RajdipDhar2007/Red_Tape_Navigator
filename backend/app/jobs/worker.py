"""Arq worker: scheduled KB refresh (diff detection), retention purge, reminder dispatch.

Run: arq app.jobs.worker.WorkerSettings
"""
from arq import cron
from arq.connections import RedisSettings

from app.agent.llm import LLM
from app.agent.research import refresh_all
from app.core.config import get_settings
from app.db.session import maker
from app.followup.reminders import dispatch_due
from app.integrations.factory import get_integrations
from app.services.privacy import purge_expired


async def refresh_rules(ctx) -> dict:
    async with maker()() as db:
        return await refresh_all(db, llm=LLM())


async def purge_job(ctx) -> int:
    async with maker()() as db:
        return await purge_expired(db)


async def reminders_job(ctx) -> int:
    async with maker()() as db:
        return await dispatch_due(db, get_integrations())


class WorkerSettings:
    functions = [refresh_rules, purge_job, reminders_job]
    cron_jobs = [
        cron(refresh_rules, weekday={0}, hour={2}, minute={0}),  # weekly, Monday 02:00
        cron(purge_job, hour={3}, minute={0}),  # daily
        cron(reminders_job, minute={0, 30}),  # every 30 minutes
    ]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url or "redis://localhost:6379/0")
