"""AES-256-GCM encryption helpers for OrgHumans profile data.

All OAuth tokens and API keys stored on-disk by OrgHumans are encrypted
with a key derived from the user's device ID and a passphrase they set at
first launch.

The key derivation salt is stored in ~/.orghumans/.keystore. The passphrase
itself is NEVER stored anywhere — it is held in memory only for the lifetime
of the app session.

Requires: `cryptography` package (already in Hermes dependencies).
"""

import base64
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Device ID — stable, per-machine identifier
# ---------------------------------------------------------------------------

_cached_device_id: Optional[str] = None


def get_device_id() -> str:
    """Return a stable, per-machine device ID.

    Built from the MAC address reported by uuid.getnode() combined with
    platform information. Not a privacy identifier — purely used as salt
    material for key derivation so the same passphrase produces different
    keys on different machines.
    """
    global _cached_device_id
    if _cached_device_id:
        return _cached_device_id
    mac = uuid.getnode()
    platform_salt = f"{os.name}-{mac}"
    _cached_device_id = hashlib.sha256(platform_salt.encode()).hexdigest()[:32]
    return _cached_device_id


# ---------------------------------------------------------------------------
# Salt management
# ---------------------------------------------------------------------------

def _get_or_create_salt(keystore_path: Path) -> bytes:
    """Load or generate the PBKDF2 salt stored in ~/.orghumans/.keystore."""
    if keystore_path.exists():
        try:
            data = json.loads(keystore_path.read_text(encoding="utf-8"))
            return base64.b64decode(data["salt"])
        except (json.JSONDecodeError, KeyError, Exception):
            pass  # Regenerate if corrupted
    # Generate a fresh 32-byte random salt
    salt = os.urandom(32)
    keystore_path.parent.mkdir(parents=True, exist_ok=True)
    keystore_path.write_text(
        json.dumps({"salt": base64.b64encode(salt).decode()}),
        encoding="utf-8",
    )
    return salt


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

_session_key: Optional[bytes] = None


def derive_key(passphrase: str, device_id: str, salt: bytes) -> bytes:
    """Derive an AES-256 key using PBKDF2-HMAC-SHA256.

    Args:
        passphrase: User-supplied passphrase (never stored).
        device_id: Per-machine identifier (from get_device_id()).
        salt: Random salt from the keystore file.

    Returns:
        32-byte key suitable for AES-256-GCM.
    """
    # Mix passphrase + device_id so the key is machine-bound
    combined = f"{passphrase}:{device_id}".encode("utf-8")
    return hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=combined,
        salt=salt,
        iterations=260_000,  # OWASP 2023 recommendation
        dklen=32,
    )


def initialize_session_key(passphrase: str, keystore_path: Path) -> None:
    """Derive and cache the session key from the passphrase.

    Called once at app startup after the user enters their passphrase.
    The key is held in memory only — cleared when the process exits.

    Args:
        passphrase: User-supplied passphrase.
        keystore_path: Path to the .keystore file (e.g. ~/.orghumans/.keystore).
    """
    global _session_key
    salt = _get_or_create_salt(keystore_path)
    device_id = get_device_id()
    _session_key = derive_key(passphrase, device_id, salt)


def clear_session_key() -> None:
    """Clear the in-memory session key (call on app close)."""
    global _session_key
    _session_key = None


def get_session_key() -> bytes:
    """Return the cached session key, raising if not initialised."""
    if _session_key is None:
        raise RuntimeError(
            "OrgHumans session key not initialised. "
            "Call initialize_session_key() before any encrypt/decrypt operation."
        )
    return _session_key


# ---------------------------------------------------------------------------
# AES-256-GCM encrypt / decrypt
# ---------------------------------------------------------------------------

def encrypt_value(plaintext: str, key: Optional[bytes] = None) -> str:
    """Encrypt a plaintext string with AES-256-GCM.

    Args:
        plaintext: The string to encrypt.
        key: 32-byte AES key. Defaults to the cached session key.

    Returns:
        Base64-encoded string: ``<nonce_b64>:<ciphertext_b64>:<tag_b64>``
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    k = key if key is not None else get_session_key()
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(k)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # AESGCM.encrypt appends the 16-byte tag to ciphertext
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]
    parts = [
        base64.b64encode(nonce).decode(),
        base64.b64encode(ciphertext).decode(),
        base64.b64encode(tag).decode(),
    ]
    return ":".join(parts)


def decrypt_value(ciphertext_b64: str, key: Optional[bytes] = None) -> str:
    """Decrypt an AES-256-GCM encrypted value produced by encrypt_value().

    Args:
        ciphertext_b64: The encoded string from encrypt_value().
        key: 32-byte AES key. Defaults to the cached session key.

    Returns:
        The original plaintext string.

    Raises:
        ValueError: If the ciphertext is malformed or authentication fails.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag

    k = key if key is not None else get_session_key()
    try:
        parts = ciphertext_b64.split(":")
        if len(parts) != 3:
            raise ValueError("Malformed ciphertext — expected nonce:ciphertext:tag")
        nonce = base64.b64decode(parts[0])
        ciphertext = base64.b64decode(parts[1])
        tag = base64.b64decode(parts[2])
        aesgcm = AESGCM(k)
        plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
        return plaintext.decode("utf-8")
    except InvalidTag:
        raise ValueError("Decryption failed: authentication tag mismatch. Wrong key or corrupted data.")
    except Exception as exc:
        raise ValueError(f"Decryption error: {exc}") from exc


# ---------------------------------------------------------------------------
# .env file helpers
# ---------------------------------------------------------------------------

def write_env_key(env_path: Path, key_name: str, plaintext_value: str) -> None:
    """Write an encrypted key-value pair to a profile's .env file.

    Creates the .env file if it does not exist. Overwrites the key if it
    already exists. Other keys in the file are preserved.

    Args:
        env_path: Absolute path to the .env file.
        key_name: Environment variable name (e.g. ``COMPOSIO_GMAIL_TOKEN``).
        plaintext_value: The plaintext value to encrypt and store.
    """
    encrypted = encrypt_value(plaintext_value)
    lines: list[str] = []
    key_written = False

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key_name}="):
                lines.append(f"{key_name}={encrypted}")
                key_written = True
            else:
                lines.append(line)

    if not key_written:
        lines.append(f"{key_name}={encrypted}")

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def remove_env_key(env_path: Path, key_name: str) -> None:
    """Remove a key from a profile's .env file.

    No-op if the key does not exist.

    Args:
        env_path: Absolute path to the .env file.
        key_name: Environment variable name to remove.
    """
    if not env_path.exists():
        return
    lines = [
        line for line in env_path.read_text(encoding="utf-8").splitlines()
        if not line.startswith(f"{key_name}=")
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_env_key(env_path: Path, key_name: str) -> Optional[str]:
    """Read and decrypt a key from a profile's .env file.

    Args:
        env_path: Absolute path to the .env file.
        key_name: Environment variable name to read.

    Returns:
        Decrypted plaintext value, or None if the key does not exist.
    """
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key_name}="):
            encrypted = line[len(key_name) + 1:]
            try:
                return decrypt_value(encrypted)
            except ValueError:
                return None  # Key exists but can't decrypt (wrong passphrase)
    return None


def write_env_key_plaintext(env_path: Path, key_name: str, value: str) -> None:
    """Write a PLAINTEXT key-value pair to a .env file (for non-secret config).

    Use this ONLY for non-sensitive values. Sensitive tokens must use
    write_env_key() which encrypts.

    Args:
        env_path: Absolute path to the .env file.
        key_name: Environment variable name.
        value: Plaintext value.
    """
    lines: list[str] = []
    key_written = False

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key_name}="):
                lines.append(f"{key_name}={value}")
                key_written = True
            else:
                lines.append(line)

    if not key_written:
        lines.append(f"{key_name}={value}")

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
