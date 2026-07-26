"""Profile lifecycle management for OrgHumans.

A profile is one isolated agent context — its own HERMES_HOME directory with
its own memory, skills, integrations, and session history. Switching profiles
switches which HERMES_HOME is active.

Profile types
-------------
- personal: Created automatically on first launch. Belongs to the user.
- org-{org_id}: One per org the user has joined. Holds org-scoped context.

The active profile is persisted in ~/.orghumans/active_profile.json so it
survives process restarts. The Hermes subprocess is expected to be restarted
with the new HERMES_HOME after each switch.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from orghumans.constants import (
    ORGHUMANS_ROOT,
    PROFILES_DIR,
    ACTIVE_PROFILE_FILE,
    DEFAULT_PROFILE_ID,
    PROFILE_TYPE_PERSONAL,
    PROFILE_TYPE_ORG,
    PROFILE_META_FILE,
    PROFILE_SCAFFOLD_FILES,
    PROFILE_SCAFFOLD_DIRS,
    get_orghumans_root,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_profiles_root() -> Path:
    """Return the root directory that contains all profile subdirectories."""
    return get_orghumans_root() / PROFILES_DIR


def get_profile_home(profile_id: str) -> Path:
    """Return the HERMES_HOME path for a given profile.

    Args:
        profile_id: Profile identifier (e.g. ``"personal"`` or ``"org-abc123"``).

    Returns:
        Absolute path: ``~/.orghumans/profiles/{profile_id}/``
    """
    return get_profiles_root() / profile_id


def get_active_profile_json_path() -> Path:
    """Return the path to the active_profile.json file."""
    return get_orghumans_root() / ACTIVE_PROFILE_FILE


# ---------------------------------------------------------------------------
# Active profile
# ---------------------------------------------------------------------------

def get_active_profile_id() -> str:
    """Return the currently active profile ID.

    Reads ~/.orghumans/active_profile.json. Defaults to 'personal' if the
    file does not exist or is malformed.

    Returns:
        Profile ID string (e.g. ``"personal"`` or ``"org-abc123-uuid456"``).
    """
    path = get_active_profile_json_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            profile_id = data.get("active", "").strip()
            if profile_id:
                return profile_id
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_PROFILE_ID


def set_active_profile(profile_id: str) -> None:
    """Set the active profile by writing active_profile.json.

    Note: The caller is responsible for restarting the Hermes subprocess
    with the new HERMES_HOME after calling this function.

    Args:
        profile_id: The profile to activate (must already exist).

    Raises:
        ValueError: If the profile does not exist.
    """
    if not profile_exists(profile_id):
        raise ValueError(
            f"Profile '{profile_id}' does not exist. "
            f"Create it before activating it."
        )
    path = get_active_profile_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"active": profile_id, "updated_at": _now_iso()}, indent=2),
        encoding="utf-8",
    )
    logger.info("Active profile set to '%s'", profile_id)


def is_orghumans_active() -> bool:
    """Return True if OrgHumans has been initialised on this machine.

    Specifically: returns True when ~/.orghumans/active_profile.json exists.
    This is False on a fresh Hermes install that has never been set up with
    OrgHumans, ensuring zero regression for standard Hermes users.
    """
    return get_active_profile_json_path().exists()


# ---------------------------------------------------------------------------
# Profile existence and metadata
# ---------------------------------------------------------------------------

def profile_exists(profile_id: str) -> bool:
    """Return True if a profile directory exists for the given profile ID."""
    return get_profile_home(profile_id).is_dir()


def get_profile_meta(profile_id: str) -> dict:
    """Read the profile_meta.json for the given profile.

    Args:
        profile_id: Profile identifier.

    Returns:
        Dict with keys: profile_id, type, display_name, created_at, provider.
        Returns an empty dict if the file does not exist or is malformed.
    """
    meta_path = get_profile_home(profile_id) / PROFILE_META_FILE
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def list_profiles() -> list[dict]:
    """Return metadata for all existing profiles, ordered by type then name.

    Personal profile always comes first, followed by org profiles
    alphabetically by display name.

    Returns:
        List of profile metadata dicts (same shape as get_profile_meta()).
    """
    profiles_root = get_profiles_root()
    if not profiles_root.exists():
        return []

    profiles: list[dict] = []
    for entry in profiles_root.iterdir():
        if entry.is_dir():
            meta = get_profile_meta(entry.name)
            if not meta:
                # Synthesise minimal metadata for directories without meta file
                meta = {
                    "profile_id": entry.name,
                    "type": PROFILE_TYPE_PERSONAL if entry.name == "personal" else PROFILE_TYPE_ORG,
                    "display_name": entry.name,
                    "created_at": None,
                }
            profiles.append(meta)

    # Sort: personal first, then org alphabetically
    def _sort_key(p: dict) -> tuple:
        is_personal = p.get("type") == PROFILE_TYPE_PERSONAL
        return (0 if is_personal else 1, p.get("display_name", "").lower())

    return sorted(profiles, key=_sort_key)


# ---------------------------------------------------------------------------
# Profile creation
# ---------------------------------------------------------------------------

def _scaffold_profile_dir(profile_home: Path, profile_id: str, profile_type: str, meta: dict) -> None:
    """Create the standard directory structure for a new profile.

    Args:
        profile_home: The HERMES_HOME path for this profile.
        profile_id: Profile identifier.
        profile_type: 'personal' or 'org'.
        meta: Full metadata dict to write to profile_meta.json.
    """
    profile_home.mkdir(parents=True, exist_ok=True)

    # Create stub files
    for filename in PROFILE_SCAFFOLD_FILES:
        stub = profile_home / filename
        if not stub.exists():
            stub.touch()

    # Create subdirectories
    for dirname in PROFILE_SCAFFOLD_DIRS:
        (profile_home / dirname).mkdir(exist_ok=True)

    # Write profile metadata
    meta_path = profile_home / PROFILE_META_FILE
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Scaffolded profile directory: %s", profile_home)


def create_personal_profile(
    display_name: str,
    provider: str,
    api_key: str,
) -> Path:
    """Create the personal profile at ~/.orghumans/profiles/personal/.

    Writes the profile directory, scaffolds required files, stores the API
    key encrypted in the profile's .env file, and sets 'personal' as the
    active profile.

    Args:
        display_name: Human-readable name for this profile (local only).
        provider: LLM provider name (e.g. 'anthropic', 'openai', 'openrouter').
        api_key: The API key for the chosen provider (encrypted at rest).

    Returns:
        Path to the newly created profile directory (its HERMES_HOME).

    Raises:
        RuntimeError: If the personal profile already exists.
    """
    profile_id = DEFAULT_PROFILE_ID
    profile_home = get_profile_home(profile_id)

    if profile_home.exists():
        raise RuntimeError(
            f"Personal profile already exists at {profile_home}. "
            "Use the existing profile or wipe it from settings."
        )

    meta = {
        "profile_id": profile_id,
        "type": PROFILE_TYPE_PERSONAL,
        "display_name": display_name,
        "provider": provider,
        "created_at": _now_iso(),
    }
    _scaffold_profile_dir(profile_home, profile_id, PROFILE_TYPE_PERSONAL, meta)

    # Store the API key encrypted in the profile .env
    _write_provider_api_key(profile_home, provider, api_key)

    # Activate this profile
    _write_active_profile_json(profile_id)

    logger.info("Created personal profile '%s' at %s", display_name, profile_home)
    return profile_home


def create_org_profile(org_id: str, org_name: str) -> Path:
    """Create an org profile directory at ~/.orghumans/profiles/org-{org_id}/.

    Called when the user creates an org or joins one via invite key.

    Args:
        org_id: The organisation's UUID.
        org_name: Human-readable org name (used as display name).

    Returns:
        Path to the newly created org profile directory.
    """
    profile_id = f"org-{org_id}"
    profile_home = get_profile_home(profile_id)
    meta = {
        "profile_id": profile_id,
        "type": PROFILE_TYPE_ORG,
        "display_name": org_name,
        "org_id": org_id,
        "created_at": _now_iso(),
    }
    _scaffold_profile_dir(profile_home, profile_id, PROFILE_TYPE_ORG, meta)
    logger.info("Created org profile for org '%s' at %s", org_id, profile_home)
    return profile_home


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _write_active_profile_json(profile_id: str) -> None:
    """Write active_profile.json without the profile existence check."""
    path = get_active_profile_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"active": profile_id, "updated_at": _now_iso()}, indent=2),
        encoding="utf-8",
    )


def _write_provider_api_key(profile_home: Path, provider: str, api_key: str) -> None:
    """Encrypt and store the LLM provider API key in the profile .env.

    The key name follows Hermes conventions:
      - anthropic  → ANTHROPIC_API_KEY
      - openai     → OPENAI_API_KEY
      - openrouter → OPENROUTER_API_KEY
      - gemini     → GEMINI_API_KEY
      - groq       → GROQ_API_KEY

    Falls back to ``{PROVIDER.upper()}_API_KEY`` for unknown providers.
    """
    _PROVIDER_KEY_MAP = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "together": "TOGETHER_API_KEY",
        "xai": "XAI_API_KEY",
    }
    env_key = _PROVIDER_KEY_MAP.get(provider.lower(), f"{provider.upper()}_API_KEY")
    env_path = profile_home / ".env"

    # Try to encrypt; fall back to plaintext with a warning if session key
    # not yet initialised (edge case: profile creation before passphrase setup)
    try:
        from orghumans.crypto import write_env_key
        write_env_key(env_path, env_key, api_key)
    except Exception:
        logger.warning(
            "Crypto not initialised — storing API key plaintext. "
            "Re-encrypt from Settings after setting up your passphrase."
        )
        from orghumans.crypto import write_env_key_plaintext
        write_env_key_plaintext(env_path, env_key, api_key)
