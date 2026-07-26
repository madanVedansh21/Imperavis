"""Local SQLite store for integration connection state.

Tracks which integrations are connected per profile, when they were connected,
their status, and (encrypted) token metadata. The actual token values are
stored encrypted in the profile's .env file via orghumans.crypto — this DB
holds only the connection state and metadata needed to render the UI quickly
without decrypting anything.

Schema
------
Table: connections
  profile_id   TEXT NOT NULL
  provider     TEXT NOT NULL
  connected_at TEXT NOT NULL  -- ISO-8601 UTC
  status       TEXT NOT NULL  -- 'active' | 'expired' | 'error'
  scopes       TEXT           -- JSON array of granted OAuth scopes
  PRIMARY KEY (profile_id, provider)
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from orghumans.profile_manager import get_profile_home

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS connections (
    profile_id   TEXT NOT NULL,
    provider     TEXT NOT NULL,
    connected_at TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    scopes       TEXT,
    PRIMARY KEY (profile_id, provider)
);
"""


def _db_path(profile_id: str) -> Path:
    """Return the integrations.db path for a given profile."""
    return get_profile_home(profile_id) / "integrations.db"


@contextmanager
def _connect(profile_id: str) -> Generator[sqlite3.Connection, None, None]:
    """Open (and auto-create) the integrations.db for a profile."""
    path = _db_path(profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Read ─────────────────────────────────────────────────────────────────────


def list_connections(profile_id: str) -> list[dict]:
    """Return all connected integrations for a profile.

    Args:
        profile_id: Profile identifier.

    Returns:
        List of dicts with keys: provider, connected_at, status, scopes.
    """
    try:
        with _connect(profile_id) as conn:
            rows = conn.execute(
                "SELECT provider, connected_at, status, scopes "
                "FROM connections WHERE profile_id = ? ORDER BY connected_at DESC",
                (profile_id,),
            ).fetchall()
            return [
                {
                    "provider": r["provider"],
                    "connected_at": r["connected_at"],
                    "status": r["status"],
                    "scopes": json.loads(r["scopes"]) if r["scopes"] else [],
                }
                for r in rows
            ]
    except sqlite3.Error as exc:
        logger.warning("integrations_db: list_connections failed for %s: %s", profile_id, exc)
        return []


def get_connection(profile_id: str, provider: str) -> Optional[dict]:
    """Return the connection record for a specific provider, or None."""
    try:
        with _connect(profile_id) as conn:
            row = conn.execute(
                "SELECT provider, connected_at, status, scopes "
                "FROM connections WHERE profile_id = ? AND provider = ?",
                (profile_id, provider),
            ).fetchone()
            if not row:
                return None
            return {
                "provider": row["provider"],
                "connected_at": row["connected_at"],
                "status": row["status"],
                "scopes": json.loads(row["scopes"]) if row["scopes"] else [],
            }
    except sqlite3.Error as exc:
        logger.warning("integrations_db: get_connection failed for %s/%s: %s", profile_id, provider, exc)
        return None


def is_connected(profile_id: str, provider: str) -> bool:
    """Return True if the provider is connected for this profile."""
    return get_connection(profile_id, provider) is not None


# ── Write ─────────────────────────────────────────────────────────────────────


def upsert_connection(
    profile_id: str,
    provider: str,
    status: str = "active",
    scopes: Optional[list[str]] = None,
) -> None:
    """Insert or update a connection record.

    Args:
        profile_id: Profile identifier.
        provider: Integration provider id (e.g. 'gmail').
        status: 'active', 'expired', or 'error'.
        scopes: OAuth scopes granted (optional).
    """
    now = datetime.now(timezone.utc).isoformat()
    scopes_json = json.dumps(scopes or [])
    try:
        with _connect(profile_id) as conn:
            conn.execute(
                """
                INSERT INTO connections (profile_id, provider, connected_at, status, scopes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, provider) DO UPDATE SET
                    status = excluded.status,
                    scopes = excluded.scopes
                """,
                (profile_id, provider, now, status, scopes_json),
            )
    except sqlite3.Error as exc:
        logger.error("integrations_db: upsert_connection failed for %s/%s: %s", profile_id, provider, exc)
        raise


def update_status(profile_id: str, provider: str, status: str) -> None:
    """Update only the status of an existing connection.

    Args:
        profile_id: Profile identifier.
        provider: Integration provider id.
        status: New status ('active', 'expired', 'error').
    """
    try:
        with _connect(profile_id) as conn:
            conn.execute(
                "UPDATE connections SET status = ? WHERE profile_id = ? AND provider = ?",
                (status, profile_id, provider),
            )
    except sqlite3.Error as exc:
        logger.error("integrations_db: update_status failed for %s/%s: %s", profile_id, provider, exc)
        raise


def delete_connection(profile_id: str, provider: str) -> None:
    """Remove a connection record entirely.

    Args:
        profile_id: Profile identifier.
        provider: Integration provider id.
    """
    try:
        with _connect(profile_id) as conn:
            conn.execute(
                "DELETE FROM connections WHERE profile_id = ? AND provider = ?",
                (profile_id, provider),
            )
    except sqlite3.Error as exc:
        logger.error("integrations_db: delete_connection failed for %s/%s: %s", profile_id, provider, exc)
        raise
