"""In-process scheduler for single-instance hosting (RUN_SCHEDULER=true): the same jobs as the Arq worker, no Redis needed.

Each run is written to the audit log (actor "system", action "job.<name>"); the last entry decides when a job is next
due, so a restart or a sleeping free-tier instance neither skips nor repeats work. Run it on ONE instance only: with
several API replicas use the Arq worker (`app/jobs/worker.py`) instead.
"""
import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.logging import get_logger
from app.db.models import AuditLog
from app.db.session import maker

log = get_logger("scheduler")
TICK_SECONDS = 60
START_DELAY_SECONDS = 20  # let the app finish starting before the first run

Job = Callable[[AsyncSession], Awaitable[object]]


async def _reminders(db: AsyncSession) -> object:
    from app.followup.reminders import dispatch_due
    from app.integrations.factory import get_integrations

    return await dispatch_due(db, get_integrations())


async def _purge(db: AsyncSession) -> object:
    from app.services.privacy import purge_expired

    return await purge_expired(db)


async def _refresh_rules(db: AsyncSession) -> object:
    from app.agent.llm import LLM
    from app.agent.research import refresh_all

    return await refresh_all(db, llm=LLM())


async def _forms(db: AsyncSession) -> object:
    from app.forms.official import check_for_changes

    return await check_for_changes(db)


# name -> (interval, job). Same cadence as WorkerSettings.cron_jobs.
JOBS: dict[str, tuple[timedelta, Job]] = {
    "reminders": (timedelta(minutes=30), _reminders),
    "purge": (timedelta(days=1), _purge),
    "refresh_rules": (timedelta(days=7), _refresh_rules),
    "forms": (timedelta(days=7), _forms),
}
# These re-fetch every official source. On a brand-new deployment they wait one full interval instead of running at boot.
DEFER_FIRST_RUN = frozenset({"refresh_rules", "forms"})


async def last_run(db: AsyncSession, name: str) -> datetime | None:
    row = (await db.execute(
        select(AuditLog).where(AuditLog.action == f"job.{name}").order_by(AuditLog.seq.desc()).limit(1)
    )).scalar_one_or_none()
    if row is None:
        return None
    return row.ts if row.ts.tzinfo else row.ts.replace(tzinfo=UTC)


async def run_due(now: datetime | None = None, jobs: dict[str, tuple[timedelta, Job]] | None = None) -> list[str]:
    """Run every job whose interval has passed since its last recorded run. Returns the names that ran."""
    now = now or datetime.now(UTC)
    ran: list[str] = []
    for name, (interval, job) in (jobs or JOBS).items():
        async with maker()() as db:
            last = await last_run(db, name)
            if last is None and name in DEFER_FIRST_RUN:
                await audit.record(db, "system", f"job.{name}", {"ok": True, "deferred": True})
                continue
            if last is not None and now - last < interval:
                continue
            ok = True
            try:
                await job(db)
            except Exception as exc:  # noqa: BLE001 - one failing job must not stop the others
                ok = False
                await db.rollback()
                log.warning("job_failed", job=name, error_type=type(exc).__name__)
            # recorded even on failure so a broken job is retried at its normal cadence, not every minute
            await audit.record(db, "system", f"job.{name}", {"ok": ok})
            ran.append(name)
    return ran


async def run_forever() -> None:
    await asyncio.sleep(START_DELAY_SECONDS)
    while True:
        try:
            await run_due()
        except Exception as exc:  # noqa: BLE001 - e.g. database briefly unreachable; try again next tick
            log.warning("scheduler_tick_failed", error_type=type(exc).__name__)
        await asyncio.sleep(TICK_SECONDS)
