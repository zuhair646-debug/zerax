"""Encryption helper for continuation-mode credentials.

All third-party access keys (Git tokens, FTP passwords, SSH keys, LLM API
keys, etc.) supplied by the user for the "Continue Project" flow are
encrypted with AES-128 (Fernet) before being stored in MongoDB. The
plaintext key is never logged, never displayed back to the user, and never
sent to the AI in raw form — the AI only sees `***encrypted***` and uses
internal handlers that decrypt on-demand to call the actual provider.
"""

from __future__ import annotations

import os
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_FERNET: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Lazy-initialise the Fernet instance from env. Fails loudly if missing
    so we never silently store plaintext."""
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    key = os.environ.get("CONTINUATION_FERNET_KEY")
    if not key:
        raise RuntimeError(
            "CONTINUATION_FERNET_KEY missing in backend/.env — "
            "credential encryption disabled, refusing to operate."
        )
    _FERNET = Fernet(key.encode() if isinstance(key, str) else key)
    return _FERNET


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a string secret. Returns base64-encoded ciphertext."""
    if not plaintext:
        raise ValueError("Cannot encrypt empty secret")
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a previously-encrypted secret. Raises InvalidToken if tampered."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.error("Fernet token invalid — possible tampering or key rotation")
        raise


def fingerprint_secret(plaintext: str) -> str:
    """SHA-256 fingerprint used to detect duplicate keys across projects
    without ever storing the plaintext. We compare fingerprints, not
    ciphertexts (Fernet ciphertexts are non-deterministic)."""
    if not plaintext:
        return ""
    return hashlib.sha256(plaintext.strip().encode("utf-8")).hexdigest()


def mask_secret(plaintext: str) -> str:
    """Return a display-safe masked version (last 4 chars only)."""
    if not plaintext:
        return ""
    t = plaintext.strip()
    if len(t) <= 4:
        return "•" * len(t)
    return "•" * 8 + t[-4:]
