"""Symmetric encryption for secrets we must store but never display in full —
third-party database passwords and webhook signing secrets, specifically.

Derives a Fernet key from settings.secret_key so no extra key-management step is
needed for local/demo use; a production deployment should instead set a dedicated,
randomly-generated ENCRYPTION_KEY and rotate it independently of the JWT secret
(noted in docs/deployment.md).
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

settings = get_settings()


def _fernet() -> Fernet:
    # Fernet needs a 32-byte urlsafe-base64 key; derive one deterministically from
    # the app secret so no separate key needs to be provisioned for local/dev use.
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt stored secret — was ENCRYPTION_KEY/SECRET_KEY rotated?") from exc
