"""Password hashing and token utilities.

Passwords are hashed with PBKDF2-HMAC-SHA256 from the Python standard library
(600,000 iterations, 16-byte random salt per password, OWASP 2023 guidance).
Hashes are stored as ``pbkdf2_sha256$<iterations>$<salt>$<hash>`` so the
work factor can be increased later without breaking existing accounts.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from functools import lru_cache

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000
SALT_BYTES = 16


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Return a salted PBKDF2 hash string for ``password``."""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Check ``password`` against a stored hash using a constant-time comparison."""
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def needs_rehash(stored_hash: str, iterations: int = DEFAULT_ITERATIONS) -> bool:
    """True when a hash was produced with an older (weaker) work factor."""
    try:
        algorithm, iterations_text, _, _ = stored_hash.split("$", 3)
        return algorithm != ALGORITHM or int(iterations_text) < iterations
    except ValueError:
        return True


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    """Hash used to equalise login timing when a username does not exist."""
    return hash_password(secrets.token_urlsafe(16))


def generate_token(nbytes: int = 18) -> str:
    """Unguessable URL-safe token (used for public share links)."""
    return secrets.token_urlsafe(nbytes)
