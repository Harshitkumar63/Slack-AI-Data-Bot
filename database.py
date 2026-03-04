"""
database.py
-----------
PostgreSQL database connection and query execution layer.

- Connects to Postgres using credentials from environment variables.
- Enforces read-only (SELECT) queries.
- Automatically appends LIMIT 20 when the caller omits it.
"""

import os
import re

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Connection helper 
# ---------------------------------------------------------------------------

def _get_connection():
    """Return a new psycopg2 connection using env-var credentials."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "analytics"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------

def _is_select_only(sql: str) -> bool:
    """Return True when the statement is a plain SELECT (no mutations)."""
    normalized = sql.strip().upper()
    # Reject anything that isn't a SELECT
    if not normalized.startswith("SELECT"):
        return False
    # Reject dangerous keywords that could appear inside sub-queries, CTEs, etc.
    dangerous = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
                 "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"}
    tokens = set(re.findall(r"\b[A-Z]+\b", normalized))
    if tokens & dangerous:
        return False
    return True


def _ensure_limit(sql: str, max_rows: int = 20) -> str:
    """Append a LIMIT clause when the query does not already contain one."""
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";")
        sql += f" LIMIT {max_rows}"
    return sql


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_query(sql: str) -> list[dict]:
    """
    Execute a read-only SQL query and return rows as a list of dicts.

    Raises
    ------
    ValueError  – if the query is not a SELECT statement.
    Exception   – any database / connection error is propagated.
    """
    if not _is_select_only(sql):
        raise ValueError("Only SELECT queries are allowed.")

    sql = _ensure_limit(sql)

    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            # Convert RealDictRow objects to plain dicts for serialisation
            return [dict(row) for row in rows]
    finally:
        conn.close()
