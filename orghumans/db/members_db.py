"""Local SQLite store for Organisation Member Roster.

Location: ~/.orghumans/orgs/{org_id}/members.db
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from orghumans.constants import ORGS_DIR, get_orghumans_root

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    org_id       TEXT NOT NULL,
    username     TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'member',  -- 'owner' | 'member'
    joined_at    TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    device_id    TEXT,
    PRIMARY KEY (org_id, username)
);
"""


def get_members_db_path(org_id: str) -> Path:
    return get_orghumans_root() / ORGS_DIR / org_id / "members.db"


@contextmanager
def _connect(org_id: str) -> Generator[sqlite3.Connection, None, None]:
    path = get_members_db_path(org_id)
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


def add_or_update_member(
    org_id: str,
    username: str,
    role: str = "member",
    device_id: Optional[str] = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect(org_id) as conn:
        conn.execute(
            """
            INSERT INTO members (org_id, username, role, joined_at, last_seen_at, device_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(org_id, username) DO UPDATE SET
                role = excluded.role,
                last_seen_at = excluded.last_seen_at,
                device_id = COALESCE(excluded.device_id, members.device_id)
            """,
            (org_id, username, role, now, now, device_id),
        )


def remove_member(org_id: str, username: str) -> None:
    with _connect(org_id) as conn:
        conn.execute(
            "DELETE FROM members WHERE org_id = ? AND username = ?",
            (org_id, username),
        )


def get_members(org_id: str) -> list[dict]:
    try:
        with _connect(org_id) as conn:
            rows = conn.execute(
                "SELECT username, role, joined_at, last_seen_at, device_id "
                "FROM members WHERE org_id = ? ORDER BY role DESC, username ASC",
                (org_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.warning("members_db: get_members failed for %s: %s", org_id, exc)
        return []


def is_member(org_id: str, username: str) -> bool:
    try:
        with _connect(org_id) as conn:
            row = conn.execute(
                "SELECT 1 FROM members WHERE org_id = ? AND username = ?",
                (org_id, username),
            ).fetchone()
            return row is not None
    except sqlite3.Error:
        return False


def get_member_role(org_id: str, username: str) -> Optional[str]:
    try:
        with _connect(org_id) as conn:
            row = conn.execute(
                "SELECT role FROM members WHERE org_id = ? AND username = ?",
                (org_id, username),
            ).fetchone()
            return row["role"] if row else None
    except sqlite3.Error:
        return None
