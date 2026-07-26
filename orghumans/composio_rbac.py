"""Composio RBAC & Shared Integration Management for Org Organisations.

Manages organisation-scoped integration connections and member permissions
(can_read, can_write) stored in ~/.orghumans/orgs/{org_id}/integrations.db.

RBAC Matrix
-----------
Table: org_integrations
  org_id        TEXT NOT NULL
  provider      TEXT NOT NULL
  connected_by  TEXT NOT NULL
  connected_at  TEXT NOT NULL
  status        TEXT NOT NULL DEFAULT 'active'
  PRIMARY KEY (org_id, provider)

Table: member_permissions
  org_id     TEXT NOT NULL
  provider   TEXT NOT NULL
  username   TEXT NOT NULL
  can_read   INTEGER NOT NULL DEFAULT 1
  can_write  INTEGER NOT NULL DEFAULT 0
  PRIMARY KEY (org_id, provider, username)
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
CREATE TABLE IF NOT EXISTS org_integrations (
    org_id       TEXT NOT NULL,
    provider     TEXT NOT NULL,
    connected_by TEXT NOT NULL,
    connected_at TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    PRIMARY KEY (org_id, provider)
);

CREATE TABLE IF NOT EXISTS member_permissions (
    org_id    TEXT NOT NULL,
    provider  TEXT NOT NULL,
    username  TEXT NOT NULL,
    can_read  INTEGER NOT NULL DEFAULT 1,
    can_write INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (org_id, provider, username)
);
"""


def get_integrations_db_path(org_id: str) -> Path:
    return get_orghumans_root() / ORGS_DIR / org_id / "integrations.db"


@contextmanager
def _connect(org_id: str) -> Generator[sqlite3.Connection, None, None]:
    path = get_integrations_db_path(org_id)
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


# ── Org Integrations ──────────────────────────────────────────────────────────


def connect_org_integration(org_id: str, provider: str, connected_by: str) -> None:
    """Register an org-scoped connected integration."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect(org_id) as conn:
        conn.execute(
            """
            INSERT INTO org_integrations (org_id, provider, connected_by, connected_at, status)
            VALUES (?, ?, ?, ?, 'active')
            ON CONFLICT(org_id, provider) DO UPDATE SET
                connected_by = excluded.connected_by,
                connected_at = excluded.connected_at,
                status = 'active'
            """,
            (org_id, provider, connected_by, now),
        )
        # By default, grant owner write + read, others read-only
        conn.execute(
            """
            INSERT INTO member_permissions (org_id, provider, username, can_read, can_write)
            VALUES (?, ?, ?, 1, 1)
            ON CONFLICT(org_id, provider, username) DO UPDATE SET
                can_read = 1,
                can_write = 1
            """,
            (org_id, provider, connected_by),
        )


def disconnect_org_integration(org_id: str, provider: str) -> None:
    with _connect(org_id) as conn:
        conn.execute("DELETE FROM org_integrations WHERE org_id = ? AND provider = ?", (org_id, provider))
        conn.execute("DELETE FROM member_permissions WHERE org_id = ? AND provider = ?", (org_id, provider))


def list_org_integrations(org_id: str) -> list[dict]:
    try:
        with _connect(org_id) as conn:
            rows = conn.execute("SELECT * FROM org_integrations WHERE org_id = ?", (org_id,)).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


# ── Member Permissions ────────────────────────────────────────────────────────


def set_member_permission(
    org_id: str,
    provider: str,
    username: str,
    can_read: bool = True,
    can_write: bool = False,
) -> None:
    with _connect(org_id) as conn:
        conn.execute(
            """
            INSERT INTO member_permissions (org_id, provider, username, can_read, can_write)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(org_id, provider, username) DO UPDATE SET
                can_read = excluded.can_read,
                can_write = excluded.can_write
            """,
            (org_id, provider, username, 1 if can_read else 0, 1 if can_write else 0),
        )


def get_member_permission(org_id: str, provider: str, username: str) -> dict:
    try:
        with _connect(org_id) as conn:
            row = conn.execute(
                "SELECT can_read, can_write FROM member_permissions WHERE org_id = ? AND provider = ? AND username = ?",
                (org_id, provider, username),
            ).fetchone()
            if row:
                return {"can_read": bool(row["can_read"]), "can_write": bool(row["can_write"])}
    except sqlite3.Error:
        pass
    return {"can_read": True, "can_write": False}  # Default fallback


def can_member_access(org_id: str, provider: str, username: str, action: str = "read") -> bool:
    perm = get_member_permission(org_id, provider, username)
    if action == "write":
        return perm["can_write"]
    return perm["can_read"]


def check_tool_permission(org_id: str, username: str, provider: str, is_write_action: bool = False) -> None:
    """Enforce RBAC check for tool execution.

    Raises PermissionError if access is denied.
    """
    action = "write" if is_write_action else "read"
    if not can_member_access(org_id, provider, username, action=action):
        raise PermissionError(
            f"Permission Denied: User @{username} lacks {action} permission for integration '{provider}' "
            f"in organisation '{org_id}'."
        )
