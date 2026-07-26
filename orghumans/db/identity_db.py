"""Local SQLite store for Organisation Identity.

Holds org_meta, brand_identity, glossary terms, and github_repos selection.

Location: ~/.orghumans/orgs/{org_id}/identity.db
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
CREATE TABLE IF NOT EXISTS org_meta (
    org_id      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    org_type    TEXT NOT NULL,
    invite_key  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    created_by  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brand_identity (
    org_id            TEXT PRIMARY KEY,
    brand_description TEXT,
    tone              TEXT,
    products_json     TEXT,
    target_audience   TEXT,
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS glossary (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id     TEXT NOT NULL,
    term       TEXT NOT NULL,
    definition TEXT NOT NULL,
    UNIQUE(org_id, term)
);

CREATE TABLE IF NOT EXISTS github_repos (
    org_id         TEXT NOT NULL,
    repo_full_name TEXT NOT NULL,
    selected       INTEGER NOT NULL DEFAULT 1,
    readme_snippet TEXT,
    issues_summary TEXT,
    PRIMARY KEY (org_id, repo_full_name)
);
"""


def get_identity_db_path(org_id: str) -> Path:
    return get_orghumans_root() / ORGS_DIR / org_id / "identity.db"


@contextmanager
def _connect(org_id: str) -> Generator[sqlite3.Connection, None, None]:
    path = get_identity_db_path(org_id)
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


def save_org_meta(org_id: str, name: str, description: str, org_type: str, invite_key: str, created_by: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect(org_id) as conn:
        conn.execute(
            """
            INSERT INTO org_meta (org_id, name, description, org_type, invite_key, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(org_id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                org_type = excluded.org_type,
                invite_key = excluded.invite_key
            """,
            (org_id, name, description, org_type, invite_key, now, created_by),
        )


def get_org_meta(org_id: str) -> Optional[dict]:
    try:
        with _connect(org_id) as conn:
            row = conn.execute("SELECT * FROM org_meta WHERE org_id = ?", (org_id,)).fetchone()
            return dict(row) if row else None
    except sqlite3.Error as exc:
        logger.warning("identity_db: get_org_meta failed for %s: %s", org_id, exc)
        return None


def save_brand_identity(
    org_id: str,
    brand_description: str = "",
    tone: str = "",
    products: Optional[list[str]] = None,
    target_audience: str = "",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    products_json = json.dumps(products or [])
    with _connect(org_id) as conn:
        conn.execute(
            """
            INSERT INTO brand_identity (org_id, brand_description, tone, products_json, target_audience, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(org_id) DO UPDATE SET
                brand_description = excluded.brand_description,
                tone = excluded.tone,
                products_json = excluded.products_json,
                target_audience = excluded.target_audience,
                updated_at = excluded.updated_at
            """,
            (org_id, brand_description, tone, products_json, target_audience, now),
        )


def set_glossary_terms(org_id: str, terms: list[dict[str, str]]) -> None:
    with _connect(org_id) as conn:
        conn.execute("DELETE FROM glossary WHERE org_id = ?", (org_id,))
        for t in terms:
            if t.get("term") and t.get("definition"):
                conn.execute(
                    "INSERT INTO glossary (org_id, term, definition) VALUES (?, ?, ?)",
                    (org_id, t["term"].strip(), t["definition"].strip()),
                )
