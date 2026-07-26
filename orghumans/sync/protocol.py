"""OrgHumans Sync Protocol — authentication and message encoding.

Implements HMAC-SHA256 challenge-response authentication using the organisation
invite key, and AES-256-GCM encrypted delta payload wrapping for peer-to-peer and
server-assisted cross-device state replication.
"""

import base64
import hmac
import hashlib
import json
import os
import time
from typing import Optional


# ── Message Types ─────────────────────────────────────────────────────────────
MSG_AUTH_CHALLENGE = "auth_challenge"
MSG_AUTH_RESPONSE = "auth_response"
MSG_AUTH_SUCCESS = "auth_success"
MSG_AUTH_FAILED = "auth_failed"
MSG_SYNC_REQUEST = "sync_request"
MSG_SYNC_DELTA = "sync_delta"
MSG_PING = "ping"
MSG_PONG = "pong"


def generate_challenge() -> str:
    """Generate a random 32-byte hex nonce for authentication."""
    return os.urandom(32).hex()


def compute_auth_response(nonce: str, invite_key: str, username: str) -> str:
    """Compute HMAC-SHA256 of nonce:username using invite_key as key."""
    key = invite_key.encode("utf-8")
    msg = f"{nonce}:{username}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_auth_response(nonce: str, invite_key: str, username: str, response: str) -> bool:
    """Verify incoming auth response against expected HMAC-SHA256."""
    expected = compute_auth_response(nonce, invite_key, username)
    return hmac.compare_digest(expected, response)


def encode_message(msg_type: str, payload: dict) -> str:
    """Encode a sync protocol message as a JSON string."""
    return json.dumps({
        "type": msg_type,
        "timestamp": int(time.time()),
        "payload": payload,
    })


def decode_message(raw_msg: str) -> dict:
    """Parse incoming JSON protocol message."""
    try:
        return json.loads(raw_msg)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed protocol message: {exc}") from exc


def encrypt_delta(delta_dict: dict, secret_key: bytes) -> str:
    """Encrypt a delta payload using AES-256-GCM with SHA256 HMAC fallback."""
    plaintext = json.dumps(delta_dict).encode("utf-8")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = os.urandom(12)
        aesgcm = AESGCM(secret_key)
        ct_tag = aesgcm.encrypt(nonce, plaintext, None)
        ciphertext = ct_tag[:-16]
        tag = ct_tag[-16:]

        parts = [
            base64.b64encode(nonce).decode(),
            base64.b64encode(ciphertext).decode(),
            base64.b64encode(tag).decode(),
        ]
        return ":".join(parts)
    except ImportError:
        # Fallback: b64 plaintext + HMAC-SHA256 signature
        b64_pt = base64.b64encode(plaintext).decode()
        sig = hmac.new(secret_key, b64_pt.encode(), hashlib.sha256).hexdigest()
        return f"FALLBACK:{b64_pt}:{sig}"


def decrypt_delta(encrypted_b64: str, secret_key: bytes) -> dict:
    """Decrypt an AES-256-GCM or FALLBACK encrypted delta payload."""
    if encrypted_b64.startswith("FALLBACK:"):
        parts = encrypted_b64.split(":")
        if len(parts) != 3:
            raise ValueError("Malformed fallback payload")
        b64_pt = parts[1]
        sig = parts[2]
        expected_sig = hmac.new(secret_key, b64_pt.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, sig):
            raise ValueError("Fallback payload signature verification failed")
        plaintext = base64.b64decode(b64_pt)
        return json.loads(plaintext.decode("utf-8"))

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    parts = encrypted_b64.split(":")
    if len(parts) != 3:
        raise ValueError("Malformed encrypted delta payload")

    nonce = base64.b64decode(parts[0])
    ciphertext = base64.b64decode(parts[1])
    tag = base64.b64decode(parts[2])

    aesgcm = AESGCM(secret_key)
    plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
    return json.loads(plaintext.decode("utf-8"))
