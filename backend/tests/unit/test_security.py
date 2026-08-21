"""
AtlasOS Phase 2 Unit Tests — Security Core.

Tests password hashing, JWT token lifecycle, and API Key generation.
"""

from uuid import uuid4

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_api_key,
    verify_password,
)


def test_password_hashing():
    """Test bcrypt password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    # Hash should be different from plaintext
    assert hashed != password
    # Verification should succeed with correct password
    assert verify_password(password, hashed) is True
    # Verification should fail with incorrect password
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_access_token():
    """Test JWT access token generation and decoding."""
    subject = str(uuid4())
    tenant_id = str(uuid4())
    role = "admin"

    token = create_access_token(
        subject=subject,
        tenant_id=tenant_id,
        role=role,
    )

    payload = decode_token(token)

    assert payload["sub"] == subject
    assert payload["type"] == "access"
    assert payload["tenant_id"] == tenant_id
    assert payload["role"] == role
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_refresh_token():
    """Test JWT refresh token generation."""
    subject = str(uuid4())

    token = create_refresh_token(subject=subject)
    payload = decode_token(token)

    assert payload["sub"] == subject
    assert payload["type"] == "refresh"
    assert "tenant_id" not in payload


def test_api_key_generation():
    """Test API key prefix, plaintext, and hashing."""
    prefix, plaintext, key_hash = generate_api_key()

    assert plaintext.startswith("atlas_")
    assert prefix == plaintext[:8]
    assert len(plaintext) > 30

    # Verification should succeed
    assert verify_api_key(plaintext, key_hash) is True
    # Verification should fail with altered key
    assert verify_api_key(plaintext + "x", key_hash) is False


def test_session_token_generation():
    """Test SHA-256 session token hashing."""
    plaintext, token_hash = generate_session_token()

    # Manual hash check
    import hashlib

    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()

    assert token_hash == expected_hash
    assert hash_session_token(plaintext) == expected_hash
