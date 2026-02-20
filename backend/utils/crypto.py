"""
Fernet-based encryption for secrets at rest (API keys, service account JSON).

Usage:
    from backend.utils.crypto import encrypt, decrypt

    cipher = encrypt("my-api-key")     # → base64 Fernet token string
    plain  = decrypt(cipher)           # → "my-api-key"

The encryption key is read from settings.encryption_key (ENCRYPTION_KEY env var).
If no key is set, a deterministic fallback is derived from the DATABASE_URL so that
dev environments work out-of-the-box — but production MUST set ENCRYPTION_KEY.
"""

import json
import hashlib
import base64
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet

from backend.config.settings import settings

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    key = settings.encryption_key
    if not key:
        # Derive a deterministic key from DATABASE_URL for dev convenience
        digest = hashlib.sha256(settings.database_url.encode()).digest()
        key = base64.urlsafe_b64encode(digest[:32]).decode()
        import logging
        logging.getLogger("crypto").warning(
            "ENCRYPTION_KEY not set — using derived key from DATABASE_URL. "
            "Set ENCRYPTION_KEY in production!"
        )
    else:
        # Ensure the key is valid Fernet format (32 url-safe base64 bytes)
        if len(key) < 32:
            digest = hashlib.sha256(key.encode()).digest()
            key = base64.urlsafe_b64encode(digest[:32]).decode()

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string → Fernet token (base64 string)."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token → plaintext string."""
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        # If decryption fails (key changed, or value was stored unencrypted),
        # return the raw value so existing data isn't lost
        return ciphertext


def encrypt_json(data: Dict[str, Any]) -> str:
    """Encrypt a dict as JSON → Fernet token string."""
    if not data:
        return ""
    return encrypt(json.dumps(data, separators=(",", ":")))


def decrypt_json(ciphertext: str) -> Dict[str, Any]:
    """Decrypt a Fernet token → dict."""
    if not ciphertext:
        return {}
    plain = decrypt(ciphertext)
    try:
        return json.loads(plain)
    except (json.JSONDecodeError, TypeError):
        # Might be raw JSON (legacy unencrypted data)
        if isinstance(plain, str) and plain.startswith("{"):
            try:
                return json.loads(plain)
            except Exception:
                pass
        return {}
