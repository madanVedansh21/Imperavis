"""Local SQLite store for Offline Sync Diff Queue.

Location: ~/.orghumans/orgs/{org_id}/sync_log.db
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from orghumans.constants import ORGS_DIR, get_orghumans_root

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pending_diffs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id     TEXT NOT NULL,
    diff_type  TEXT NOT NULL,
    payload    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_sync_log_db_path(org_id: str) -> Path:
    return get_orghumans_root() / ORGS_DIR / org_id / "sync_log.db"


@contextmanager
def _connect(org_id: str) -> Generator[sqlite3.Connection, None, None]:
    path = get_sync_log_db_path(org_id)
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


def enqueue_diff(org_id: str, diff_type: str, payload: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect(org_id) as conn:
        conn.execute(
            "INSERT INTO pending_diffs (org_id, diff_type, payload, created_at) VALUES (?, ?, ?, ?)",
            (org_id, diff_type, json.dumps(payload), now),
        )


def peek_pending_diffs(org_id: str, limit: int = 50) -> list[dict]:
    try:
        with _connect(org_id) as conn:
            rows = conn.execute(
                "SELECT id, diff_type, payload, created_at FROM pending_diffs WHERE org_id = ? ORDER BY id ASC LIMIT ?",
                (org_id, limit),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "diff_type": r["diff_type"],
                    "payload": json.loads(r["payload"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
    except sqlite3.Error:
        return []


def clear_diffs_up_to(org_id: str, max_id: int) -> None:
    with _connect(org_id) as conn:
        conn.execute("DELETE FROM pending_diffs WHERE org_id = ? AND id <= ?", (org_id, max_id))
