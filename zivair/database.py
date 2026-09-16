"""
Thin data-access layer over SQLite.

Nothing in this module knows about Streamlit or about the business domain -
it only opens connections, runs SQL and hands back rows or DataFrames.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable, Sequence

import pandas as pd

from .config import DB_PATH, SCHEMA_PATH


def connect(db_path=DB_PATH) -> sqlite3.Connection:
    """Open a connection with the settings this project always wants."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite needs this per-connection
    return conn


@contextmanager
def get_connection(db_path=DB_PATH):
    """`with get_connection() as conn:` - commits on success, rolls back on error."""
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    """Drop and recreate every table from schema.sql."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def query_df(sql: str, params: Sequence[Any] = (), db_path=DB_PATH) -> pd.DataFrame:
    """Run a SELECT and return the result as a DataFrame."""
    conn = connect(db_path)
    try:
        return pd.read_sql_query(sql, conn, params=tuple(params))
    finally:
        conn.close()


def query_one(sql: str, params: Sequence[Any] = (), db_path=DB_PATH) -> sqlite3.Row | None:
    """Run a SELECT and return the first row (or None)."""
    conn = connect(db_path)
    try:
        return conn.execute(sql, tuple(params)).fetchone()
    finally:
        conn.close()


def execute(sql: str, params: Sequence[Any] = (), db_path=DB_PATH) -> int:
    """Run a single INSERT/UPDATE/DELETE. Returns the number of affected rows."""
    with get_connection(db_path) as conn:
        cur = conn.execute(sql, tuple(params))
        return cur.rowcount


def execute_many(sql: str, rows: Iterable[Sequence[Any]], db_path=DB_PATH) -> None:
    """Bulk INSERT - used by the data generator."""
    with get_connection(db_path) as conn:
        conn.executemany(sql, rows)


def database_exists(db_path=DB_PATH) -> bool:
    """True once the file exists and actually contains our tables."""
    if not db_path.exists():
        return False
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='flights'"
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def table_counts(db_path=DB_PATH) -> dict[str, int]:
    """Row count per table - handy for sanity checks and for the docs."""
    conn = connect(db_path)
    try:
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    finally:
        conn.close()
