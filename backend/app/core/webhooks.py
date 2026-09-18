"""HMAC signing for inbound webhooks (#5) — verifies that a payload claiming to be
from a company's system was actually signed with that endpoint's own secret,
without requiring a login session (there's no human on the other end)."""
from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_token() -> str:
    return secrets.token_urlsafe(24)


def generate_secret() -> str:
    return secrets.token_urlsafe(32)


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify(body: bytes, secret: str, provided_signature: str) -> bool:
    expected = sign(body, secret)
    return hmac.compare_digest(expected, provided_signature)
