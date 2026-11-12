"""Safe PostgreSQL backup and non-production restore-verification tooling.

Usage examples:
  # 1. Create a compressed, timestamped custom-format backup (uses DATABASE_URL):
  python scripts/db_backup_restore.py backup --output-dir ./backups

  # 2. Dry-run backup command inspection (never prints passwords):
  python scripts/db_backup_restore.py backup --output-dir ./backups --dry-run

  # 3. Restore into a dedicated non-production verification database and verify schema:
  CONFIRM_NON_PROD_RESTORE=YES_RESTORE_NON_PROD python scripts/db_backup_restore.py restore-verify \\
      --dump-file ./backups/rtn-backup-20261112T020000Z.dump \\
      --target-url postgresql://rtn:secret@localhost:5432/rtn_restore \\
      --confirm-non-prod-restore

Safety guarantees:
- Passwords are never passed on the command line or printed to stdout/stderr; PGPASSWORD is set only in the subprocess environment.
- Restore refuses to run when APP_ENV=prod, when confirmation flag/env is missing, when the target matches DATABASE_URL,
  when the target host/db contains production markers, or when the target database name does not end with an explicit
  verification suffix (_restore, _verify, _test, _scratch, _dr).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

CONFIRM_ENV_VAR = "CONFIRM_NON_PROD_RESTORE"
CONFIRM_ENV_VALUE = "YES_RESTORE_NON_PROD"
ALLOWED_RESTORE_DB_SUFFIXES = ("_restore", "_verify", "_test", "_scratch", "_dr")
FORBIDDEN_PROD_TOKENS = ("prod", "production", "primary", "live", "master", "main")


class BackupRestoreSafetyError(RuntimeError):
    """Raised when a backup or restore operation violates a safety precondition."""


@dataclass(frozen=True)
class CommandPlan:
    args: list[str]
    redacted_args: list[str]
    pgpassword: str | None
    output_file: str | None = None
    verify_args: list[str] | None = None


def build_backup_filename(prefix: str = "rtn-backup", now: datetime | None = None) -> str:
    ts = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    safe_prefix = re.sub(r"[^A-Za-z0-9_-]", "-", prefix).strip("-") or "rtn-backup"
    return f"{safe_prefix}-{ts}.dump"


def normalize_pg_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise BackupRestoreSafetyError("Database URL is empty.")
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgresql+psycopg2://", "postgres://"):
        if raw.startswith(prefix):
            raw = "postgresql://" + raw[len(prefix) :]
            break
    if not raw.startswith("postgresql://"):
        raise BackupRestoreSafetyError("Only PostgreSQL database URLs are supported by pg_dump / pg_restore.")
    parsed = urlsplit(raw)
    if not parsed.hostname or not parsed.path or parsed.path == "/":
        raise BackupRestoreSafetyError("PostgreSQL URL must include a hostname and database name.")
    return raw


def _strip_password(parsed: SplitResult, mask: str | None) -> str:
    user = parsed.username or ""
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    if user:
        auth = f"{user}:{mask}@" if (parsed.password is not None and mask is not None) else f"{user}@"
    else:
        auth = ""
    return urlunsplit((parsed.scheme, f"{auth}{host}{port}", parsed.path, parsed.query, ""))


def redact_db_url(url: str) -> str:
    """Return a copy of the database URL safe for logs (password replaced with [REDACTED])."""
    try:
        norm = normalize_pg_url(url)
    except BackupRestoreSafetyError:
        return re.sub(r"://([^:/@\s]+):([^@\s]+)@", r"://\1:[REDACTED]@", url or "")
    return _strip_password(urlsplit(norm), mask="[REDACTED]")


def extract_passwordless_dsn(url: str) -> tuple[str, str | None, str, str]:
    """Return (passwordless_dsn, password, hostname, dbname)."""
    norm = normalize_pg_url(url)
    parsed = urlsplit(norm)
    dsn = _strip_password(parsed, mask=None)
    dbname = parsed.path.lstrip("/")
    return dsn, parsed.password, (parsed.hostname or "").lower(), dbname


def build_backup_plan(
    database_url: str,
    output_dir: str | Path = "./backups",
    filename: str | None = None,
    now: datetime | None = None,
) -> CommandPlan:
    dsn, password, _, _ = extract_passwordless_dsn(database_url)
    out_dir = Path(output_dir)
    fname = filename or build_backup_filename(now=now)
    out_path = str(out_dir / fname)
    args = [
        "pg_dump",
        "--format=custom",
        "--compress=6",
        "--no-owner",
        "--no-acl",
        f"--file={out_path}",
        dsn,
    ]
    redacted_args = [*args[:-1], redact_db_url(database_url)]
    return CommandPlan(args=args, redacted_args=redacted_args, pgpassword=password, output_file=out_path)


def validate_restore_target(
    *,
    target_url: str,
    primary_url: str = "",
    app_env: str = "dev",
    confirm_flag: bool = False,
    confirm_env: str = "",
) -> tuple[str, str | None]:
    """Validate that a restore target is explicitly confirmed and strictly non-production."""
    if app_env.strip().lower() in ("prod", "production"):
        raise BackupRestoreSafetyError(
            "Refusing to run restore verification when APP_ENV is 'prod'. Run restore verification in an isolated non-prod environment."
        )
    if not confirm_flag or confirm_env.strip() != CONFIRM_ENV_VALUE:
        raise BackupRestoreSafetyError(
            f"Restore verification requires both --confirm-non-prod-restore and {CONFIRM_ENV_VAR}={CONFIRM_ENV_VALUE}."
        )
    target_dsn, target_pw, target_host, target_db = extract_passwordless_dsn(target_url)

    if primary_url.strip():
        primary_dsn, _, primary_host, primary_db = extract_passwordless_dsn(primary_url)
        if target_dsn == primary_dsn or (target_host == primary_host and target_db.lower() == primary_db.lower()):
            raise BackupRestoreSafetyError(
                "Refusing to restore into the active primary DATABASE_URL. Specify a separate verification database."
            )

    db_lower = target_db.lower()
    host_tokens = set(re.split(r"[^a-z0-9]+", target_host))
    db_tokens = set(re.split(r"[^a-z0-9]+", db_lower))
    if (host_tokens | db_tokens) & set(FORBIDDEN_PROD_TOKENS):
        raise BackupRestoreSafetyError(
            f"Refusing to restore: target host or database name ('{target_db}') contains a production marker."
        )
    if not db_lower.endswith(ALLOWED_RESTORE_DB_SUFFIXES):
        raise BackupRestoreSafetyError(
            f"Refusing to restore: target database '{target_db}' must end with one of {ALLOWED_RESTORE_DB_SUFFIXES}."
        )
    return target_dsn, target_pw


def build_restore_plan(
    *,
    dump_file: str | Path,
    target_url: str,
    primary_url: str = "",
    app_env: str = "dev",
    confirm_flag: bool = False,
    confirm_env: str = "",
) -> CommandPlan:
    target_dsn, target_pw = validate_restore_target(
        target_url=target_url,
        primary_url=primary_url,
        app_env=app_env,
        confirm_flag=confirm_flag,
        confirm_env=confirm_env,
    )
    dump_path = str(Path(dump_file))
    restore_args = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        "--exit-on-error",
        f"--dbname={target_dsn}",
        dump_path,
    ]
    redacted_restore = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        "--exit-on-error",
        f"--dbname={redact_db_url(target_url)}",
        dump_path,
    ]
    verify_sql = (
        "SELECT version_num FROM alembic_version; "
        "SELECT count(*) AS claims_count FROM claims; "
        "SELECT count(*) AS audit_rows FROM audit_log;"
    )
    verify_args = [
        "psql",
        "--no-psqlrc",
        "-v",
        "ON_ERROR_STOP=1",
        f"--dbname={target_dsn}",
        "-c",
        verify_sql,
    ]
    return CommandPlan(
        args=restore_args,
        redacted_args=redacted_restore,
        pgpassword=target_pw,
        output_file=dump_path,
        verify_args=verify_args,
    )


def execute_plan(plan: CommandPlan, *, dry_run: bool = False) -> dict[str, object]:
    if dry_run:
        return {"ok": True, "dry_run": True, "command": plan.redacted_args, "output_file": plan.output_file}
    if plan.output_file and plan.args[0] == "pg_dump":
        Path(plan.output_file).parent.mkdir(parents=True, exist_ok=True)
    elif plan.output_file and plan.args[0] == "pg_restore" and not Path(plan.output_file).is_file():
        raise BackupRestoreSafetyError(f"Backup dump file does not exist: {plan.output_file}")

    env = os.environ.copy()
    if plan.pgpassword is not None:
        env["PGPASSWORD"] = plan.pgpassword
    try:
        subprocess.run(plan.args, env=env, check=True, capture_output=True, text=True)  # noqa: S603
        if plan.verify_args:
            subprocess.run(plan.verify_args, env=env, check=True, capture_output=True, text=True)  # noqa: S603
    except subprocess.CalledProcessError as exc:
        raise BackupRestoreSafetyError(
            f"{plan.args[0]} failed with exit code {exc.returncode}."
        ) from exc
    return {"ok": True, "dry_run": False, "command": plan.redacted_args, "output_file": plan.output_file}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe PostgreSQL backup and restore-verification utility.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b_p = sub.add_parser("backup", help="Create a compressed custom-format PostgreSQL backup.")
    b_p.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    b_p.add_argument("--output-dir", default="./backups")
    b_p.add_argument("--dry-run", action="store_true")

    r_p = sub.add_parser("restore-verify", help="Restore a dump into a dedicated non-prod verification DB and verify schema.")
    r_p.add_argument("--dump-file", required=True)
    r_p.add_argument("--target-url", default=os.environ.get("RESTORE_TARGET_DATABASE_URL", ""))
    r_p.add_argument("--primary-url", default=os.environ.get("DATABASE_URL", ""))
    r_p.add_argument("--confirm-non-prod-restore", action="store_true")
    r_p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "backup":
            plan = build_backup_plan(args.database_url, output_dir=args.output_dir)
        else:
            plan = build_restore_plan(
                dump_file=args.dump_file,
                target_url=args.target_url,
                primary_url=args.primary_url,
                app_env=os.environ.get("APP_ENV", "dev"),
                confirm_flag=args.confirm_non_prod_restore,
                confirm_env=os.environ.get(CONFIRM_ENV_VAR, ""),
            )
        res = execute_plan(plan, dry_run=args.dry_run)
        print(f"OK: {' '.join(str(x) for x in res['command'])}")  # noqa: T201
        return 0
    except BackupRestoreSafetyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)  # noqa: T201
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

