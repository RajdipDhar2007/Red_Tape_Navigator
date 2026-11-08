"""An old local SQLite file (created before login lockout existed) must be upgraded in place, not crash login."""
import sqlite3

from sqlalchemy import create_engine, inspect

from app.db.models import Base
from app.db.sqlite_upgrade import add_missing_columns


def make_old_db(path) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE users (id VARCHAR(32) PRIMARY KEY, email VARCHAR(255) NOT NULL, password_hash VARCHAR(255) NOT NULL, "
                "role VARCHAR(32) NOT NULL, language VARCHAR(8) NOT NULL, created_at DATETIME NOT NULL, deleted_at DATETIME)")
    con.execute("INSERT INTO users VALUES ('u1', 'old@example.com', 'x', 'citizen', 'en', '2026-01-01 00:00:00', NULL)")
    con.commit()
    con.close()


def test_adds_missing_columns_keeps_rows_and_is_idempotent(tmp_path):
    db = tmp_path / "old.db"
    make_old_db(db)
    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        first = add_missing_columns(conn)
        second = add_missing_columns(conn)
    assert {"users.failed_logins", "users.locked_until"} <= set(first)
    assert second == []
    with engine.connect() as conn:
        cols = {c["name"] for c in inspect(conn).get_columns("users")}
        assert {"failed_logins", "locked_until"} <= cols
        row = conn.exec_driver_sql("SELECT email, failed_logins, locked_until FROM users").one()
    assert tuple(row) == ("old@example.com", 0, None)  # existing account kept, counter defaults to zero


def test_does_nothing_for_a_current_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'new.db'}")
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        assert add_missing_columns(conn) == []
