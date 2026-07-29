"""Composio integration client for OrgHumans personal profiles.

Wraps the Composio Python SDK to provide:
  - A static catalogue of available integrations (works with no SDK)
  - OAuth flow: initiate → callback → store token
  - Disconnect: remove token from .env + remove DB record
  - Token validity check

Composio SDK dependency
-----------------------
The SDK (`composio-core`) is optional. If not installed, `initiate_oauth()`,
`handle_oauth_callback()`, and `check_token_validity()` raise a clear error.
`list_available_integrations()` and `get_connected_integrations()` always work
regardless of SDK presence.

Install: pip install composio-core
"""

import logging
import os
from pathlib import Path
from typing import Optional

from orghumans.db.integrations_db import (
    delete_connection,
    is_connected,
    list_connections,
    upsert_connection,
)
from orghumans.crypto import remove_env_key, write_env_key_plaintext
from orghumans.profile_manager import get_profile_home

logger = logging.getLogger(__name__)

# ── Static integration catalogue ──────────────────────────────────────────────
#
# These are shown in the UI regardless of whether Composio SDK is installed.
# Composio provider IDs match their official app slugs.

_CATALOGUE: list[dict] = [
    # Productivity / Google
    {"id": "gmail", "name": "Gmail", "description": "Read, send and manage emails.", "category": "Email", "icon": "📧", "color": "#EA4335"},
    {"id": "googlecalendar", "name": "Google Calendar", "description": "Read and create calendar events.", "category": "Calendar", "icon": "📅", "color": "#4285F4"},
    {"id": "googledrive", "name": "Google Drive", "description": "Access and manage files in Drive.", "category": "Storage", "icon": "📁", "color": "#34A853"},
    {"id": "googlesheets", "name": "Google Sheets", "description": "Read and write spreadsheet data.", "category": "Productivity", "icon": "📊", "color": "#0F9D58"},
    {"id": "googledocs", "name": "Google Docs", "description": "Create and edit documents.", "category": "Productivity", "icon": "📝", "color": "#4285F4"},
     # Communication
    {"id": "slack", "name": "Slack", "description": "Send messages and read channels.", "category": "Communication", "icon": "💬", "color": "#4A154B"},
    {"id": "zoom", "name": "Zoom", "description": "Schedule and manage Zoom meetings.", "category": "Communication", "icon": "📹", "color": "#2D8CFF"},
    {"id": "microsoftteams", "name": "Microsoft Teams", "description": "Send messages and join meetings.", "category": "Communication", "icon": "👥", "color": "#6264A7"},
    {"id": "outlook", "name": "Outlook", "description": "Read and send Outlook emails.", "category": "Email", "icon": "📨", "color": "#0078D4"}
    {"id": "googlemeet", "name": "Google Meet", "description": "Join and host Google Meet meetings.", "category": "Communication", "icon": "📹", "color": "#2D8CFF"},,
    # Dev tools
    {"id": "github", "name": "GitHub", "description": "Manage repos, issues, and PRs.", "category": "Development", "icon": "🐙", "color": "#24292F"},    # Project management
    {"id": "notion", "name": "Notion", "description": "Read and write Notion pages.", "category": "Productivity", "icon": "📓", "color": "#000000"},
    {"id": "trello", "name": "Trello", "description": "Manage Trello boards and cards.", "category": "Productivity", "icon": "📋", "color": "#0052CC"},
    # CRM / Sales
    {"id": "hubspot", "name": "HubSpot", "description": "Manage contacts and deals in HubSpot.", "category": "CRM", "icon": "🧡", "color": "#FF7A59"},
    {"id": "salesforce", "name": "Salesforce", "description": "Access Salesforce records and objects.", "category": "CRM", "icon": "☁️", "color": "#00A1E0"},
    # Social
    {"id": "reddit", "name": "Reddit", "description": "Read subreddits, submit posts and comments.", "category": "Social", "icon": "🤖", "color": "#FF4500"},
    {"id": "linkedin", "name": "LinkedIn", "description": "Manage LinkedIn connections and posts.", "category": "Social", "icon": "👔", "color": "#0077B5"},
]


def list_available_integrations() -> list[dict]:
    """Return the full static catalogue of available integrations.

    This never requires the Composio SDK — it always works.

    Returns:
        List of integration dicts with keys:
        id, name, description, category, icon, color.
    """
    return _CATALOGUE


def get_connected_integrations(profile_id: str) -> list[dict]:
    """Return integrations that are currently connected for this profile.

    Reads from the local integrations.db — no network call, no SDK needed.

    Args:
        profile_id: Profile identifier.

    Returns:
        List of dicts: provider, connected_at, status, scopes.
    """
    return list_connections(profile_id)


# ── Composio SDK helpers ───────────────────────────────────────────────────────

def _get_composio_toolset(profile_id: str):
    """Return a ComposioToolSet scoped to the given profile's .env.

    Attempts lazy installation via lazy_deps if composio-core is not installed.
    """
    try:
        from composio import ComposioToolSet  # type: ignore[import]
    except ImportError:
        try:
            from tools.lazy_deps import ensure
            ensure("orghumans.composio")
            from composio import ComposioToolSet  # type: ignore[import]
        except Exception as exc:
            raise ImportError(
                "composio-core is not installed. Run: pip install composio-core"
            ) from exc

    composio_key = get_composio_api_key(profile_id)

    if not composio_key:
        raise RuntimeError(
            f"COMPOSIO_API_KEY not found for profile '{profile_id}'."
        )

    return ComposioToolSet(api_key=composio_key)


# ── OAuth flow ─────────────────────────────────────────────────────────────────

_OAUTH_REDIRECT_URI = "http://localhost:49152/callback"


def initiate_oauth(provider: str, profile_id: str) -> str:
    """Initiate an OAuth flow for the given provider."""
    try:
        toolset = _get_composio_toolset(profile_id)
        entity = toolset.get_entity(id=profile_id)
        request = entity.initiate_connection(
            app_name=provider.upper(),
            redirect_url=f"{_OAUTH_REDIRECT_URI}?state={provider}",
        )
        url = getattr(request, "redirect_url", None) or getattr(request, "redirectUrl", None)
        if url:
            logger.info("OAuth initiated via SDK for %s/%s", provider, profile_id)
            return url
    except Exception as exc:
        logger.warning("Composio SDK initiate_connection failed for %s/%s: %s — using direct portal URL", provider, profile_id, exc)

    # Record the connection attempt in local DB so UI shows it connected
    # NOTE: Do NOT mark as connected here — user hasn't completed OAuth yet.
    # The UI will mark it connected after the user confirms in their browser.

    # Fallback to direct Composio App portal link
    return f"https://app.composio.dev/apps/{provider.lower()}"


def handle_oauth_callback(provider: str, code: str, profile_id: str) -> None:
    """Complete the OAuth flow after the redirect callback.

    Called by the Electron main process OAuth server after it catches the
    redirect from the system browser.

    Args:
        provider: Composio provider slug.
        code: Authorization code from the OAuth redirect.
        profile_id: Profile identifier.
    """
    try:
        toolset = _get_composio_toolset(profile_id)
        entity = toolset.get_entity(id=profile_id)

        # Exchange the code for a connected account
        # The Composio SDK handles token exchange internally
        connection = entity.get_connection(app_name=provider.upper())
        if not connection:
            # Some providers need explicit code exchange
            toolset.complete_connection(provider.upper(), code)

        # Record the connection in the local DB
        upsert_connection(profile_id, provider, status="active")
        logger.info("OAuth callback completed for %s/%s", provider, profile_id)

    except (ImportError, RuntimeError):
        raise
    except Exception as exc:
        logger.error("handle_oauth_callback failed for %s/%s: %s", provider, profile_id, exc)
        upsert_connection(profile_id, provider, status="error")
        raise RuntimeError(f"OAuth callback handling failed for {provider}: {exc}") from exc


# ── Disconnect ─────────────────────────────────────────────────────────────────

def disconnect_integration(provider: str, profile_id: str) -> None:
    """Disconnect an integration from this profile.

    Removes the connection record from integrations.db and clears the
    associated token keys from the profile .env.

    Args:
        provider: Composio provider slug.
        profile_id: Profile identifier.
    """
    profile_home = get_profile_home(profile_id)
    env_path = profile_home / ".env"

    # Remove known token key patterns for this provider
    token_keys = [
        f"{provider.upper()}_ACCESS_TOKEN",
        f"{provider.upper()}_REFRESH_TOKEN",
        f"COMPOSIO_{provider.upper()}_TOKEN",
    ]
    for key in token_keys:
        try:
            remove_env_key(env_path, key)
        except Exception as exc:
            logger.debug("Could not remove %s from .env: %s", key, exc)

    # NOTE: We intentionally skip the Composio SDK revoke call here.
    # The SDK import can hang for 20+ seconds if composio-core is not installed
    # or the network is slow. The DB delete below is always the authoritative
    # disconnect action from the desktop app's perspective.

    # Always remove from local DB
    delete_connection(profile_id, provider)
    logger.info("Disconnected %s from profile %s", provider, profile_id)


# ── Token validity ─────────────────────────────────────────────────────────────

def check_token_validity(provider: str, profile_id: str) -> bool:
    """Check whether the stored token for a provider is still valid.

    Makes a lightweight API call via Composio SDK to verify the token.
    Falls back to the local DB status if SDK is unavailable.

    Args:
        provider: Composio provider slug.
        profile_id: Profile identifier.

    Returns:
        True if the token is valid and active, False otherwise.
    """
    try:
        toolset = _get_composio_toolset(profile_id)
        entity = toolset.get_entity(id=profile_id)
        connection = entity.get_connection(app_name=provider.upper())
        valid = bool(connection and getattr(connection, "status", "") == "ACTIVE")
        # Sync status back to local DB
        if is_connected(profile_id, provider):
            from orghumans.db.integrations_db import update_status
            update_status(profile_id, provider, "active" if valid else "expired")
        return valid

    except ImportError:
        # SDK not installed — trust local DB
        from orghumans.db.integrations_db import get_connection
        record = get_connection(profile_id, provider)
        return record is not None and record.get("status") == "active"
    except Exception as exc:
        logger.warning("check_token_validity failed for %s/%s: %s", provider, profile_id, exc)
        return False


# ── Composio API key management ────────────────────────────────────────────────

def set_composio_api_key(profile_id: str, api_key: str) -> None:
    """Store the Composio API key for a profile.

    Writes the key plaintext to the profile .env (Composio API keys are
    public-facing API tokens, not OAuth secrets — they can be stored
    plaintext in the .env the same way LLM provider keys are).

    Args:
        profile_id: Profile identifier.
        api_key: Composio API key from https://app.composio.dev/settings.
    """
    profile_home = get_profile_home(profile_id)
    env_path = profile_home / ".env"
    write_env_key_plaintext(env_path, "COMPOSIO_API_KEY", api_key)
    logger.info("Composio API key set for profile %s", profile_id)


MASTER_COMPOSIO_API_KEY = ""


def get_composio_api_key(profile_id: str) -> Optional[str]:
    """Return the Composio API key for a profile.

    Checks process environment and the profile's .env file.
    Returns None if no key is configured.
    """
    # 1. Check process environment
    env_override = os.environ.get("COMPOSIO_API_KEY", "").strip()
    if env_override:
        return env_override

    # 2. Check profile's local .env
    profile_home = get_profile_home(profile_id)
    env_path = profile_home / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("COMPOSIO_API_KEY="):
                val = line[len("COMPOSIO_API_KEY="):].strip()
                if val:
                    return val

    # 3. No fallback — return None
    return None


def has_composio_api_key(profile_id: str) -> bool:
    """Return True if a Composio API key is configured for this profile."""
    return bool(get_composio_api_key(profile_id))
