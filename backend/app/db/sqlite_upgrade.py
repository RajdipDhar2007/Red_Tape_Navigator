"""Dev/test convenience for SQLite only: add columns that newer code expects but an old local database file lacks.

``Base.metadata.create_all`` creates missing TABLES but never adds missing COLUMNS, so a database file created by an older
version of the app made every query on that table fail (the UI showed "Could not sign in"). Production uses Alembic
(``make migrate``); this helper is never used there. It only ever ADDS columns; it never drops or alters anything.
"""
import logging

from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from app.db.models import Base

log = logging.getLogger(__name__)


def add_missing_columns(conn: Connection) -> list[str]:
    """ALTER TABLE ... ADD COLUMN for every model column missing from an existing table. Returns what was added."""
    if conn.dialect.name != "sqlite":
        return []
    insp = inspect(conn)
    added: list[str] = []
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue  # create_all makes whole tables
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in have:
                continue
            default = getattr(getattr(col, "default", None), "arg", None)
            if isinstance(default, bool):
                default = int(default)
            if isinstance(default, int | float | str):
                clause = f" DEFAULT {default!r}" if isinstance(default, str) else f" DEFAULT {default}"
            elif col.nullable:
                clause = ""
            else:
                log.warning("cannot auto-add NOT NULL column %s.%s without a default; run alembic or recreate the dev database",
                            table.name, col.name)
                continue
            not_null = " NOT NULL" if (not col.nullable and clause) else ""
            conn.exec_driver_sql(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col.type.compile(conn.dialect)}{not_null}{clause}')
            added.append(f"{table.name}.{col.name}")
    if added:
        log.warning("upgraded old local SQLite schema: added %s", ", ".join(added))
    return added
