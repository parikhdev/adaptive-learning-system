"""
app/db/connection.py
Single persistent connection — Supabase Session Mode Pooler
Port  : 6543 (resolved SSL/IPv6 timeout on Mac M4)
"""
import psycopg2
import psycopg2.extras
import logging
from app.config import settings

log = logging.getLogger(__name__)

_conn: psycopg2.extensions.connection = None


def _build_connection() -> psycopg2.extensions.connection:
    """
    Build a fresh psycopg2 connection using settings.DB_* fields.
    Single source of truth for connection params.
    """
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        sslmode="require",
        options="-c client_encoding=UTF8",
    )
    conn.autocommit = False
    return conn


def init_pool():
    global _conn
    _conn = _build_connection()
    log.info("Database connection established.")


def close_pool():
    """Close connection cleanly at app shutdown."""
    global _conn
    if _conn and not _conn.closed:
        _conn.close()
        log.info("Database connection closed.")


def get_connection() -> psycopg2.extensions.connection:
    """
    Return active connection.
    Auto-reconnects if connection was dropped (network blip, pooler timeout).
    """
    global _conn
    if _conn is None or _conn.closed:
        log.warning("Connection lost — reconnecting...")
        _conn = _build_connection()
        log.info("Reconnected successfully.")
    return _conn


def execute_query(sql: str, params=None) -> list[dict]:
    """
    Execute SELECT query.
    Returns list of dicts keyed by column name.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        conn.rollback()
        log.error(f"Query failed: {e}")
        raise


def execute_write(sql: str, params=None) -> None:
    """
    Execute INSERT / UPDATE / DELETE.
    Auto-commits on success, rolls back on failure.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.error(f"Write failed: {e}")
        raise


def execute_write_returning(sql: str, params=None) -> dict | None:
    """
    Execute INSERT ... RETURNING.
    Returns the created/updated row as a dict.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            result = cur.fetchone()
        conn.commit()
        return dict(result) if result else None
    except Exception as e:
        conn.rollback()
        log.error(f"Write returning failed: {e}")
        raise