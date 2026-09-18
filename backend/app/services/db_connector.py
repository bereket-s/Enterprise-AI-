"""Generic read-only database connector (#2 of the six integration paths).

A company gives us a connection (host/credentials) plus either a table name or a
SELECT statement; we open a short-lived SQLAlchemy engine against *their*
database, read the rows into a DataFrame, and hand that off to the same
generic ingestion functions every other integration path uses. The connection
is never held open between syncs — each sync opens, reads, and disposes it.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.crypto import decrypt_secret
from app.models.integration import DatabaseConnection

_DRIVER_BY_DIALECT = {
    "postgresql": "postgresql+psycopg2",
    "mysql": "mysql+pymysql",
    "mssql": "mssql+pyodbc",
    "oracle": "oracle+cx_oracle",
    "sqlite": "sqlite",
}

# Only a single SELECT statement (or a bare table name) is ever allowed — this is a
# read-only integration, so anything else (DDL/DML, multiple statements) is rejected
# before it ever reaches the company's database.
_SAFE_SELECT_RE = re.compile(r"^\s*SELECT\s", re.IGNORECASE)
_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _build_engine(conn: DatabaseConnection) -> Engine:
    driver = _DRIVER_BY_DIALECT.get(conn.dialect)
    if driver is None:
        raise ValueError(f"Unsupported dialect '{conn.dialect}'")
    if conn.dialect == "sqlite":
        # SQLite has no user/host/port — by convention the file path is stored in `host`.
        path = Path(conn.host).as_posix()
        url = f"{driver}:///{path}"
        return create_engine(url, pool_pre_ping=True)
    password = decrypt_secret(conn.encrypted_password)
    url = f"{driver}://{conn.username}:{password}@{conn.host}:{conn.port}/{conn.database_name}"
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})


def _resolve_query(source_query: str) -> str:
    stripped = source_query.strip().rstrip(";")
    if ";" in stripped:
        raise ValueError("Only a single statement is permitted (no ';'-separated multi-statements)")
    if _SAFE_SELECT_RE.match(stripped):
        return stripped
    if _TABLE_NAME_RE.match(stripped):
        return f"SELECT * FROM {stripped}"
    raise ValueError("source_query must be a bare table name or a single SELECT statement")


def test_connection(conn: DatabaseConnection) -> dict:
    engine = _build_engine(conn)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"ok": True, "message": "Connection succeeded"}
    except Exception as exc:  # pragma: no cover - depends on an external DB being reachable
        return {"ok": False, "message": str(exc)}
    finally:
        engine.dispose()


def fetch_rows(conn: DatabaseConnection, limit: int = 50_000) -> pd.DataFrame:
    engine = _build_engine(conn)
    try:
        query = _resolve_query(conn.source_query)
        with engine.connect() as connection:
            df = pd.read_sql(text(query), connection)
        return df.head(limit)
    finally:
        engine.dispose()
