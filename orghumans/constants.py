"""OrgHumans directory layout constants and path helpers.

Import-safe — no dependencies beyond stdlib. Can be imported from anywhere
without risk of circular imports.
"""

import os
import sys
from pathlib import Path


def get_orghumans_root() -> Path:
    """Return the OrgHumans root directory.

    Platform layout:
      - Windows: %LOCALAPPDATA%\\orghumans
      - POSIX:   ~/.orghumans

    Override via ORGHUMANS_HOME env var for testing or custom installs.
    """
    override = os.environ.get("ORGHUMANS_HOME", "").strip()
    if override:
        return Path(override)
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        return base / "orghumans"
    return Path.home() / ".orghumans"


# Eager root — usable as a module-level constant
ORGHUMANS_ROOT: Path = get_orghumans_root()

# Subdirectory names
PROFILES_DIR = "profiles"
ORGS_DIR = "orgs"
ACTIVE_PROFILE_FILE = "active_profile.json"
KEYSTORE_FILE = ".keystore"
APP_CONFIG_FILE = "app_config.json"

# Profile types
PROFILE_TYPE_PERSONAL = "personal"
PROFILE_TYPE_ORG = "org"

# Default profile id
DEFAULT_PROFILE_ID = "personal"

# Files scaffolded into each profile's HERMES_HOME
PROFILE_SCAFFOLD_FILES = [
    "MEMORY.md",
    "USER.md",
    "SOUL.md",
]
PROFILE_SCAFFOLD_DIRS = [
    "skills",
]

# Profile meta filename (lives inside the profile's HERMES_HOME)
PROFILE_META_FILE = "profile_meta.json"

# Org meta filename (lives inside the org's directory)
ORG_META_FILE = "meta.json"

# Invite key format: XXXX-XXXX-XXXX
INVITE_KEY_SEGMENT_LENGTH = 4
INVITE_KEY_SEGMENTS = 3
INVITE_KEY_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars
