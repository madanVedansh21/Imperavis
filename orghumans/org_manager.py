"""Organisation lifecycle management for OrgHumans.

Handles creating an organisation, generating invite keys, joining an organisation via key,
creating org profiles, reading metadata, and listing joined orgs.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from orghumans.constants import (
    INVITE_KEY_CHARSET,
    INVITE_KEY_SEGMENT_LENGTH,
    INVITE_KEY_SEGMENTS,
    ORG_META_FILE,
    ORGS_DIR,
    PROFILE_TYPE_ORG,
    get_orghumans_root,
)
from orghumans.db.identity_db import get_org_meta as get_db_org_meta, save_brand_identity, save_org_meta, set_glossary_terms
from orghumans.db.members_db import add_or_update_member, get_members
from orghumans.profile_manager import create_org_profile, get_profile_meta, set_active_profile

logger = logging.getLogger(__name__)


def generate_invite_key() -> str:
    """Generate an invite key in the format XXXX-XXXX-XXXX."""
    segments = []
    for _ in range(INVITE_KEY_SEGMENTS):
        seg = "".join(random.choices(INVITE_KEY_CHARSET, k=INVITE_KEY_SEGMENT_LENGTH))
        segments.append(seg)
    return "-".join(segments)


def get_org_dir(org_id: str) -> Path:
    return get_orghumans_root() / ORGS_DIR / org_id


def get_org_meta_file_path(org_id: str) -> Path:
    return get_org_dir(org_id) / ORG_META_FILE


def create_org(
    name: str,
    description: str,
    org_type: str,
    creator_username: str,
    brand_identity: Optional[dict] = None,
    glossary: Optional[list[dict]] = None,
) -> dict:
    """Create a new organisation locally on this machine.

    Args:
        name: Name of the organisation.
        description: Brief description.
        org_type: Category (e.g. 'Startup', 'Agency', 'Enterprise').
        creator_username: Desired handle/username for the creator.
        brand_identity: Optional brand info dict.
        glossary: Optional list of {term, definition}.

    Returns:
        Dict containing org_id, name, invite_key, profile_id, and meta.
    """
    org_id = str(uuid.uuid4())
    invite_key = generate_invite_key()
    org_dir = get_org_dir(org_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "org_id": org_id,
        "name": name,
        "description": description,
        "org_type": org_type,
        "invite_key": invite_key,
        "created_at": now,
        "created_by": creator_username,
    }

    # 1. Save meta.json
    get_org_meta_file_path(org_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # 2. Save into SQLite identity.db
    save_org_meta(org_id, name, description, org_type, invite_key, creator_username)

    if brand_identity:
        save_brand_identity(
            org_id=org_id,
            brand_description=brand_identity.get("brand_description", ""),
            tone=brand_identity.get("tone", ""),
            products=brand_identity.get("products", []),
            target_audience=brand_identity.get("target_audience", ""),
        )

    if glossary:
        set_glossary_terms(org_id, glossary)

    # 3. Add creator as owner in members.db
    add_or_update_member(org_id, creator_username, role="owner")

    # 4. Create the corresponding isolated org profile under profiles/org-{org_id}/
    profile_home = create_org_profile(org_id, name)
    profile_id = f"org-{org_id}"

    # Save extra metadata into profile_meta.json
    profile_meta = get_profile_meta(profile_id)
    profile_meta.update({"username": creator_username, "role": "owner"})
    meta_path = profile_home / "profile_meta.json"
    meta_path.write_text(json.dumps(profile_meta, indent=2), encoding="utf-8")

    # Switch to this org profile
    set_active_profile(profile_id)

    logger.info("Created org '%s' (%s) with invite key %s", name, org_id, invite_key)
    return {
        "org_id": org_id,
        "name": name,
        "invite_key": invite_key,
        "profile_id": profile_id,
        "meta": meta,
    }


def join_org_by_invite_key(invite_key: str, username: str, remote_org_meta: Optional[dict] = None) -> dict:
    """Join an organisation using an invite key.

    If remote_org_meta is passed (from sync server or local verification), it uses that info.

    Args:
        invite_key: Format XXXX-XXXX-XXXX
        username: Chosen username for this member within the org.
        remote_org_meta: Metadata fetched from sync server or provided locally.

    Returns:
        Dict with status and profile_id.
    """
    clean_key = invite_key.strip().upper()
    
    # 1. Search locally if org was created on this machine
    orgs_root = get_orghumans_root() / ORGS_DIR
    matched_org_id = None
    matched_name = "Organisation"

    if remote_org_meta and remote_org_meta.get("org_id"):
        matched_org_id = remote_org_meta["org_id"]
        matched_name = remote_org_meta.get("name", "Organisation")
    elif orgs_root.exists():
        for d in orgs_root.iterdir():
            if d.is_dir():
                m = get_db_org_meta(d.name)
                if m and m.get("invite_key", "").upper() == clean_key:
                    matched_org_id = d.name
                    matched_name = m.get("name", "Organisation")
                    remote_org_meta = m
                    break

    if not matched_org_id:
        # Synthesize org_id from key hash if mock/testing without sync server
        matched_org_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"orghumans-{clean_key}"))
        if not remote_org_meta:
            remote_org_meta = {
                "org_id": matched_org_id,
                "name": f"Org-{clean_key[:4]}",
                "description": "Joined organisation",
                "org_type": "Joined",
                "invite_key": clean_key,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": "owner",
            }
            matched_name = remote_org_meta["name"]

    # Save org directory locally
    org_dir = get_org_dir(matched_org_id)
    org_dir.mkdir(parents=True, exist_ok=True)
    get_org_meta_file_path(matched_org_id).write_text(json.dumps(remote_org_meta, indent=2), encoding="utf-8")

    save_org_meta(
        matched_org_id,
        remote_org_meta.get("name", matched_name),
        remote_org_meta.get("description", ""),
        remote_org_meta.get("org_type", "General"),
        clean_key,
        remote_org_meta.get("created_by", "owner"),
    )

    # Add member as member
    add_or_update_member(matched_org_id, username, role="member")

    # Create profile
    profile_home = create_org_profile(matched_org_id, matched_name)
    profile_id = f"org-{matched_org_id}"

    profile_meta = get_profile_meta(profile_id)
    profile_meta.update({"username": username, "role": "member"})
    (profile_home / "profile_meta.json").write_text(json.dumps(profile_meta, indent=2), encoding="utf-8")

    set_active_profile(profile_id)
    return {
        "org_id": matched_org_id,
        "name": matched_name,
        "profile_id": profile_id,
        "role": "member",
    }


def list_joined_orgs() -> list[dict]:
    orgs_root = get_orghumans_root() / ORGS_DIR
    if not orgs_root.exists():
        return []
    res = []
    for d in orgs_root.iterdir():
        if d.is_dir():
            m = get_db_org_meta(d.name)
            if m:
                res.append(m)
    return res
