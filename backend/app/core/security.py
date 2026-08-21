"""
AtlasOS Security Utilities.

Centralizes all cryptographic operations: password hashing, JWT token
lifecycle management, and API key generation/verification.

Design decisions:
  - bcrypt for passwords: Industry standard, adaptive work factor, resistant
    to GPU-accelerated brute-force attacks. Work factor 12 provides ~250ms
    hash time, balancing security with UX on login.
  - python-jose for JWT: Supports HS256/RS256, compact token format.
    Access tokens are short-lived (30 min) to minimize exposure window.
    Refresh tokens are long-lived (7 days) and stored server-side.
  - API key format: "atlas_" prefix + 32 random bytes (base64url).
    Prefix enables key identification in logs and key scanners (e.g.,
    GitHub secret scanning). Only the bcrypt hash is persisted.
  - SHA-256 for session tokens: Lighter than bcrypt since session tokens
    are high-entropy random values (not user-chosen passwords).

Security invariants:
  - Plaintext API keys are NEVER logged or stored after initial generation.
  - JWT secret keys MUST be rotated via environment variables, not hardcoded.
  - All token expiry checks use UTC to prevent timezone-related bypasses.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

import bcrypt

# API key prefix — enables identification in logs and secret scanners.
API_KEY_PREFIX = "atlas_"
API_KEY_BYTE_LENGTH = 32  # 256 bits of randomness


# =============================================================================
# Password Hashing
# =============================================================================


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        plain_password: The user's plaintext password.

    Returns:
        The bcrypt hash string.
    """
    pwd_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The user's plaintext password attempt.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


# =============================================================================
# JWT Token Management
# =============================================================================


def create_access_token(
    subject: str,
    tenant_id: str | None = None,
    role: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a short-lived JWT access token.

    The subject is typically the user's UUID string. Additional claims
    encode the current tenant context and role for RBAC enforcement.

    Args:
        subject: Token subject (user UUID as string).
        tenant_id: Current tenant UUID as string (if tenant context is set).
        role: User's role within the tenant (admin, member, read_only).
        extra_claims: Additional claims to embed in the token.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    if tenant_id is not None:
        claims["tenant_id"] = tenant_id
    if role is not None:
        claims["role"] = role
    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(  # type: ignore
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    """
    Create a long-lived JWT refresh token.

    Refresh tokens contain minimal claims (subject + type + expiry).
    They are used exclusively to obtain new access tokens without
    re-authenticating.

    Args:
        subject: Token subject (user UUID as string).

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    claims: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(  # type: ignore
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Verifies the signature and expiration. Does NOT verify business-logic
    claims (e.g., whether the user still exists or is active). Those
    checks are performed by the auth dependency layer.

    Args:
        token: The raw JWT string.

    Returns:
        Decoded token payload as a dictionary.

    Raises:
        AuthenticationError: If the token is invalid, expired, or malformed.
    """
    settings = get_settings()
    try:
        return jwt.decode(  # type: ignore
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        raise AuthenticationError(
            message="Invalid or expired token.",
            detail={"reason": str(e)},
        ) from e


# =============================================================================
# API Key Management
# =============================================================================


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key with prefix, plaintext, and hash.

    The plaintext key is returned ONCE to the caller and must be displayed
    to the user immediately. It is NEVER stored or logged.

    Returns:
        A tuple of (prefix, plaintext_key, key_hash):
          - prefix: First 8 characters for identification (e.g., "atlas_ab").
          - plaintext_key: The full key to display to the user.
          - key_hash: The bcrypt hash to store in the database.
    """
    random_part = secrets.token_urlsafe(API_KEY_BYTE_LENGTH)
    plaintext_key = f"{API_KEY_PREFIX}{random_part}"
    prefix = plaintext_key[:8]
    key_hash = _pwd_context.hash(plaintext_key)
    return prefix, plaintext_key, key_hash


def verify_api_key(plaintext_key: str, key_hash: str) -> bool:
    """
    Verify a plaintext API key against its stored bcrypt hash.

    Args:
        plaintext_key: The API key provided in the request header.
        key_hash: The stored bcrypt hash from the database.

    Returns:
        True if the key matches, False otherwise.
    """
    return _pwd_context.verify(plaintext_key, key_hash)  # type: ignore


# =============================================================================
# Session Token Management
# =============================================================================


def generate_session_token() -> tuple[str, str]:
    """
    Generate a cryptographically secure session token and its SHA-256 hash.

    The plaintext token is stored in the client-side cookie. Only the
    SHA-256 hash is stored in the database. SHA-256 is used instead of
    bcrypt because session tokens are high-entropy random values (not
    user-chosen passwords), so dictionary attacks are not a concern.

    Returns:
        A tuple of (plaintext_token, token_hash).
    """
    plaintext_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(plaintext_token.encode()).hexdigest()
    return plaintext_token, token_hash


def hash_session_token(plaintext_token: str) -> str:
    """
    Hash a session token using SHA-256.

    Args:
        plaintext_token: The raw session token string.

    Returns:
        The SHA-256 hex digest.
    """
    return hashlib.sha256(plaintext_token.encode()).hexdigest()
