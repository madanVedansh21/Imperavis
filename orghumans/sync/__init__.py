"""OrgHumans Peer & Cross-Device Sync Layer.

Replicates organisation identity, member lists, and connected integrations
across machines securely via HMAC-SHA256 authenticated WebSocket connections and
AES-256-GCM encrypted delta payloads.
"""

from orghumans.sync.client import OrghumansSyncClient
from orghumans.sync.protocol import (
    compute_auth_response,
    decrypt_delta,
    encrypt_delta,
    generate_challenge,
    verify_auth_response,
)
from orghumans.sync.server import OrghumansSyncServer

__all__ = [
    "OrghumansSyncServer",
    "OrghumansSyncClient",
    "generate_challenge",
    "compute_auth_response",
    "verify_auth_response",
    "encrypt_delta",
    "decrypt_delta",
]
