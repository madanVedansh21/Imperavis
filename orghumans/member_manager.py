"""Member roster and permission status management for OrgHumans.
"""

import logging
from typing import Optional

from orghumans.db.members_db import (
    add_or_update_member,
    get_member_role,
    get_members,
    is_member as db_is_member,
    remove_member as db_remove_member,
)

logger = logging.getLogger(__name__)


def list_org_members(org_id: str) -> list[dict]:
    return get_members(org_id)


def is_username_available(org_id: str, username: str) -> bool:
    clean = username.strip().lower()
    members = get_members(org_id)
    return not any(m["username"].lower() == clean for m in members)


def join_member(org_id: str, username: str, role: str = "member") -> None:
    add_or_update_member(org_id, username, role=role)


def remove_org_member(org_id: str, username: str) -> None:
    db_remove_member(org_id, username)


def check_role(org_id: str, username: str) -> Optional[str]:
    return get_member_role(org_id, username)
