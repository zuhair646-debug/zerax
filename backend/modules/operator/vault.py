"""
Encrypted credentials vault
───────────────────────────
Secrets (GitHub tokens, Railway API keys, Mongo URLs, ...) are stored encrypted-at-rest
using Fernet (AES-128-CBC + HMAC-SHA256). The symmetric key is derived from JWT_SECRET
via HKDF, so rotating JWT_SECRET rotates the vault.

Usage:
    token = encrypt("ghp_xxxx")     # stored in DB
    raw   = decrypt(token)          # used at runtime, never logged
"""
import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def _derive_key() -> bytes:
    secret = (os.environ.get("JWT_SECRET") or "change-me").encode("utf-8")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"zitex-operator-vault-v1",
        info=b"fernet",
    )
    raw = hkdf.derive(secret)
    return base64.urlsafe_b64encode(raw)


_fernet = Fernet(_derive_key())


def encrypt(plain: str) -> str:
    """Encrypt a plaintext secret. Returns a url-safe token string."""
    if plain is None or plain == "":
        return ""
    return _fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt a token back to plaintext. Returns '' on failure (never raises)."""
    if not token:
        return ""
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask(plain_or_token: str, keep: int = 4) -> str:
    """
    Mask a secret for UI display. Shows last `keep` characters only.
    Works on either plaintext or decrypted value (caller decides).
    """
    if not plain_or_token:
        return ""
    if len(plain_or_token) <= keep:
        return "•" * len(plain_or_token)
    return "•" * 8 + plain_or_token[-keep:]
