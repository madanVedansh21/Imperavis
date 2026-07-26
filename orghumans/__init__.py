"""OrgHumans — profile isolation and org management layer for Hermes agent.

Public API
----------
get_orghumans_root()        → Path  — ~/.orghumans root directory
get_active_profile_id()     → str   — currently active profile id
set_active_profile(id)      → None  — switch active profile
get_profile_home(id)        → Path  — HERMES_HOME for a given profile
is_orghumans_active()       → bool  — True if orghumans is initialised

Org management:
create_org(...)
join_org_by_invite_key(...)
list_joined_orgs()
generate_invite_key()

Composio RBAC:
connect_org_integration(...)
disconnect_org_integration(...)
list_org_integrations(...)
set_member_permission(...)
get_member_permission(...)
can_member_access(...)
check_tool_permission(...)
"""

from orghumans.composio_rbac import (
    can_member_access,
    check_tool_permission,
    connect_org_integration,
    disconnect_org_integration,
    get_member_permission,
    list_org_integrations,
    set_member_permission,
)
from orghumans.constants import ORGHUMANS_ROOT, get_orghumans_root
from orghumans.org_manager import (
    create_org,
    generate_invite_key,
    join_org_by_invite_key,
    list_joined_orgs,
)
from orghumans.profile_manager import (
    create_org_profile,
    create_personal_profile,
    get_active_profile_id,
    get_profile_home,
    get_profile_meta,
    is_orghumans_active,
    list_profiles,
    profile_exists,
    set_active_profile,
)

__all__ = [
    "ORGHUMANS_ROOT",
    "get_orghumans_root",
    "get_active_profile_id",
    "set_active_profile",
    "get_profile_home",
    "is_orghumans_active",
    "list_profiles",
    "create_personal_profile",
    "create_org_profile",
    "profile_exists",
    "get_profile_meta",
    "create_org",
    "generate_invite_key",
    "join_org_by_invite_key",
    "list_joined_orgs",
    "connect_org_integration",
    "disconnect_org_integration",
    "list_org_integrations",
    "set_member_permission",
    "get_member_permission",
    "can_member_access",
    "check_tool_permission",
]
