"""Build the Organisation Context string injected into the Hermes system prompt.

This module reads the local identity.db for the active org profile and formats
it as a markdown string that is appended to the Hermes system prompt when an
org profile is active.

Design constraints
------------------
- This module is imported lazily inside prompt_builder.py to avoid circular imports.
- The output is ADDITIVE to the existing system prompt — nothing is replaced.
- If called for a personal profile or when OrgHumans is not active, returns "".
- The org agent cannot write to identity.db via any tool (read-only context).
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from orghumans.constants import get_orghumans_root, ORGS_DIR

logger = logging.getLogger(__name__)


def get_org_dir(org_id: str) -> Path:
    """Return the local directory for a given org."""
    return get_orghumans_root() / ORGS_DIR / org_id


def get_identity_db_path(org_id: str) -> Path:
    """Return the path to the org's identity.db."""
    return get_org_dir(org_id) / "identity.db"


def get_members_db_path(org_id: str) -> Path:
    """Return the path to the org's members.db."""
    return get_org_dir(org_id) / "members.db"


def get_integrations_db_path(org_id: str) -> Path:
    """Return the path to the org's integrations.db."""
    return get_org_dir(org_id) / "integrations.db"


# ---------------------------------------------------------------------------
# DB read helpers
# ---------------------------------------------------------------------------

def _read_org_meta(org_id: str) -> dict:
    """Read org metadata from identity.db."""
    db_path = get_identity_db_path(org_id)
    if not db_path.exists():
        return {}
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM org_meta WHERE org_id = ? LIMIT 1", (org_id,)
            ).fetchone()
            return dict(row) if row else {}
    except sqlite3.Error as exc:
        logger.warning("Failed to read org_meta for %s: %s", org_id, exc)
        return {}


def _read_brand_identity(org_id: str) -> dict:
    """Read brand identity from identity.db."""
    db_path = get_identity_db_path(org_id)
    if not db_path.exists():
        return {}
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM brand_identity WHERE org_id = ? LIMIT 1", (org_id,)
            ).fetchone()
            return dict(row) if row else {}
    except sqlite3.Error as exc:
        logger.warning("Failed to read brand_identity for %s: %s", org_id, exc)
        return {}


def _read_glossary(org_id: str) -> list[dict]:
    """Read glossary entries from identity.db."""
    db_path = get_identity_db_path(org_id)
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT term, definition FROM glossary WHERE org_id = ? ORDER BY term",
                (org_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.warning("Failed to read glossary for %s: %s", org_id, exc)
        return []


def _read_github_repos(org_id: str) -> list[dict]:
    """Read selected GitHub repos from identity.db."""
    db_path = get_identity_db_path(org_id)
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT repo_full_name, readme_snippet, issues_summary "
                "FROM github_repos WHERE org_id = ? AND selected = 1",
                (org_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.warning("Failed to read github_repos for %s: %s", org_id, exc)
        return []


def _read_members(org_id: str) -> list[dict]:
    """Read member list from members.db."""
    db_path = get_members_db_path(org_id)
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT username, role FROM members WHERE org_id = ? ORDER BY role DESC, username",
                (org_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.warning("Failed to read members for %s: %s", org_id, exc)
        return []


def _read_member_integrations(org_id: str, username: str) -> list[dict]:
    """Read integrations accessible to a specific member."""
    db_path = get_integrations_db_path(org_id)
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT oi.provider, mp.can_read, mp.can_write
                FROM org_integrations oi
                LEFT JOIN member_permissions mp
                  ON oi.org_id = mp.org_id
                  AND oi.provider = mp.provider
                  AND mp.username = ?
                WHERE oi.org_id = ?
                """,
                (username, org_id),
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.warning("Failed to read member integrations for %s/%s: %s", org_id, username, exc)
        return []


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_org_context(
    org_id: str,
    username: Optional[str] = None,
    role: Optional[str] = None,
) -> str:
    """Build the Organisation Context markdown block for the system prompt.

    Reads the local identity.db, members.db, and integrations.db for the
    given org and formats them into a markdown string.

    Args:
        org_id: The organisation's UUID.
        username: The current user's username within this org.
        role: The current user's role ('owner' or 'member').

    Returns:
        A markdown string to append to the system prompt, or "" if the org
        data is not available locally.
    """
    meta = _read_org_meta(org_id)
    if not meta:
        logger.debug("No org meta found for %s — skipping org context injection", org_id)
        return ""

    brand = _read_brand_identity(org_id)
    glossary = _read_glossary(org_id)
    repos = _read_github_repos(org_id)
    members = _read_members(org_id)

    lines: list[str] = [
        "## Organisation Context",
        "",
        f"**Organisation:** {meta.get('name', '')} ({meta.get('org_type', '')})",
    ]

    if meta.get("description"):
        lines.append(f"**Description:** {meta['description']}")

    if brand.get("brand_description"):
        lines.append(f"**What we do:** {brand['brand_description']}")

    if brand.get("tone"):
        lines.append(f"**Brand tone:** {brand['tone']}")

    if brand.get("products_json"):
        try:
            products = json.loads(brand["products_json"])
            if products:
                lines.append("**Products/Services:**")
                for p in products:
                    lines.append(f"  - {p}")
        except (json.JSONDecodeError, TypeError):
            pass

    if brand.get("target_audience"):
        lines.append(f"**Target audience:** {brand['target_audience']}")

    if glossary:
        lines.append("**Brand glossary:**")
        for entry in glossary:
            lines.append(f"  - **{entry['term']}**: {entry['definition']}")

    if repos:
        lines.append("")
        lines.append("**GitHub repositories (org context):**")
        for repo in repos:
            lines.append(f"  - `{repo['repo_full_name']}`")
            if repo.get("readme_snippet"):
                snippet = repo["readme_snippet"][:300].replace("\n", " ")
                lines.append(f"    README: {snippet}...")

    lines.append("")
    if username:
        lines.append(f"**Your role:** @{username} ({role or 'member'})")

    if members:
        member_handles = [f"@{m['username']}" for m in members]
        lines.append(f"**Team members:** {', '.join(member_handles)}")

    if username:
        integrations = _read_member_integrations(org_id, username)
        if integrations:
            lines.append("**Connected integrations (your access):**")
            for integ in integrations:
                if integ.get("can_read") or integ.get("can_write"):
                    access = "read+write" if integ.get("can_write") else "read"
                    lines.append(f"  - {integ['provider']} ({access})")

    lines.append("")
    lines.append(
        "_This context is injected automatically. The agent cannot directly modify "
        "org identity or permissions — those are managed through the OrgHumans UI._"
    )

    return "\n".join(lines)


def build_org_context_for_active_profile() -> str:
    """Build org context for the currently active org profile.

    Convenience function that reads the active profile from
    active_profile.json and extracts the org_id from the profile metadata.

    Returns:
        Org context string, or "" if the active profile is personal or
        OrgHumans is not initialised.
    """
    try:
        from orghumans.profile_manager import (
            is_orghumans_active,
            get_active_profile_id,
            get_profile_meta,
        )

        if not is_orghumans_active():
            return ""

        profile_id = get_active_profile_id()
        meta = get_profile_meta(profile_id)
        if meta.get("type") != "org":
            return ""

        org_id = meta.get("org_id", "")
        if not org_id:
            return ""

        username = meta.get("username")
        role = meta.get("role")
        return build_org_context(org_id, username=username, role=role)

    except Exception as exc:
        logger.warning("Failed to build org context: %s", exc)
        return ""
