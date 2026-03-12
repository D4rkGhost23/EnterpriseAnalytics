"""
Unit Tests for Authentication Service
Tests: User registration, login, password hashing, JWT token creation/validation
"""
import pytest
from datetime import datetime, timezone, timedelta

from core.config import settings
from core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token
)
from models.user import User, Tenant, UserRole
from schemas.auth import UserRegister, UserLogin
from services.auth_service import register_user, login_user, refresh_tokens
from fastapi import HTTPException


@pytest.fixture
def test_user_data():
    """Sample user registration data."""
    return UserRegister(
        email="testuser@example.com",
        password="SecurePassword123!@#",
        full_name="Test User",
        tenant_name="Test Company"
    )


@pytest.fixture
def test_login_data():
    """Sample login credentials."""
    return UserLogin(
        email="testuser@example.com",
        password="SecurePassword123!@#"
    )


# ─────────────────────────────────────────────────────────────
# TESTS: Password Hashing & Verification
# ─────────────────────────────────────────────────────────────

def test_hash_password_creates_non_plaintext():
    """Verify password hash is not plaintext."""
    password = "MyPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > len(password)


def test_verify_password_success():
    """Verify valid password passes verification."""
    password = "MyPassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_failure():
    """Verify incorrect password fails verification."""
    password = "MyPassword123!"
    hashed = hash_password(password)
    assert verify_password("WrongPassword", hashed) is False


def test_verify_password_case_sensitive():
    """Password verification is case-sensitive."""
    password = "MyPassword123!"
    hashed = hash_password(password)
    assert verify_password("mypassword123!", hashed) is False


# ─────────────────────────────────────────────────────────────
# TESTS: JWT Token Creation & Validation
# ─────────────────────────────────────────────────────────────

def test_create_access_token():
    """Verify access token is created with correct structure."""
    data = {"sub": "user123", "tenant_id": 1, "role": UserRole.ANALYST}
    token = create_access_token(data)

    assert isinstance(token, str)
    assert len(token) > 0
    # Token should be JWT format (3 parts separated by dots)
    assert token.count(".") == 2


def test_create_refresh_token():
    """Verify refresh token is created with correct structure."""
    data = {"sub": "user123", "tenant_id": 1}
    token = create_refresh_token(data)

    assert isinstance(token, str)
    assert len(token) > 0
    assert token.count(".") == 2


def test_decode_access_token():
    """Verify access token can be decoded and contains payload."""
    original_data = {"sub": "user123", "tenant_id": 1, "role": UserRole.ANALYST}
    token = create_access_token(original_data)
    decoded = decode_token(token)

    assert decoded["sub"] == original_data["sub"]
    assert decoded["tenant_id"] == original_data["tenant_id"]
    assert decoded["role"] == original_data["role"]
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_decode_refresh_token():
    """Verify refresh token can be decoded."""
    original_data = {"sub": "user123", "tenant_id": 1}
    token = create_refresh_token(original_data)
    decoded = decode_token(token)

    assert decoded["sub"] == original_data["sub"]
    assert decoded["type"] == "refresh"


def test_decode_invalid_token():
    """Verify invalid token raises exception."""
    invalid_token = "invalid.token.here"
    with pytest.raises(HTTPException):
        decode_token(invalid_token)


def test_decode_expired_token():
    """Verify expired token raises exception."""
    data = {"sub": "user123"}
    # Create token with expired timestamp
    from jose import jwt
    expired_data = data.copy()
    expired_data["exp"] = datetime.now(timezone.utc) - timedelta(hours=1)
    token = jwt.encode(expired_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(HTTPException):
        decode_token(token)


# ─────────────────────────────────────────────────────────────
# TESTS: User Registration
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_new_user(test_db, test_user_data):
    """Verify new user registration creates user and tenant."""
    user = await register_user(test_user_data, test_db)

    assert user.email == test_user_data.email
    assert user.full_name == test_user_data.full_name
    assert user.role == UserRole.OWNER  # First user in tenant is OWNER
    assert user.is_active is True
    assert verify_password(test_user_data.password, user.hashed_password)


@pytest.mark.asyncio
async def test_register_duplicate_email(test_db, test_user_data):
    """Verify duplicate email registration raises exception."""
    await register_user(test_user_data, test_db)
    await test_db.commit()

    with pytest.raises(HTTPException):
        await register_user(test_user_data, test_db)


@pytest.mark.asyncio
async def test_register_second_user_same_tenant(test_db, test_user_data):
    """Verify second user in same tenant gets ANALYST role."""
    await register_user(test_user_data, test_db)
    await test_db.commit()

    second_user_data = UserRegister(
        email="seconduser@example.com",
        password="AnotherPassword123!@#",
        full_name="Second User",
        tenant_name=test_user_data.tenant_name  # Same tenant
    )

    second_user = await register_user(second_user_data, test_db)
    assert second_user.role == UserRole.ANALYST


@pytest.mark.asyncio
async def test_register_password_hash_not_plaintext(test_db, test_user_data):
    """Verify password is hashed, not stored plaintext."""
    user = await register_user(test_user_data, test_db)

    assert user.hashed_password != test_user_data.password
    assert len(user.hashed_password) > len(test_user_data.password)


# ─────────────────────────────────────────────────────────────
# TESTS: User Login
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_valid_credentials(test_db, test_user_data, test_login_data):
    """Verify login with valid credentials succeeds."""
    await register_user(test_user_data, test_db)
    await test_db.commit()

    result = await login_user(test_login_data, test_db)

    assert "access_token" in result
    assert "refresh_token" in result
    assert result["user"].email == test_login_data.email


@pytest.mark.asyncio
async def test_login_invalid_email(test_db, test_login_data):
    """Verify login with non-existent email fails."""
    with pytest.raises(HTTPException) as exc_info:
        await login_user(test_login_data, test_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_password(test_db, test_user_data, test_login_data):
    """Verify login with wrong password fails."""
    await register_user(test_user_data, test_db)
    await test_db.commit()

    bad_login = UserLogin(email=test_user_data.email, password="WrongPassword123!@#")

    with pytest.raises(HTTPException) as exc_info:
        await login_user(bad_login, test_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_deactivated_account(test_db, test_user_data, test_login_data):
    """Verify login fails for deactivated accounts."""
    user = await register_user(test_user_data, test_db)
    user.is_active = False
    await test_db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await login_user(test_login_data, test_db)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_login_updates_last_login(test_db, test_user_data, test_login_data):
    """Verify login updates user's last_login timestamp."""
    user = await register_user(test_user_data, test_db)
    user.last_login = None
    await test_db.commit()

    await login_user(test_login_data, test_db)
    await test_db.refresh(user)

    assert user.last_login is not None


# ─────────────────────────────────────────────────────────────
# TESTS: Token Refresh
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_tokens_valid(test_db, test_user_data):
    """Verify refresh token generates new access token."""
    user = await register_user(test_user_data, test_db)
    await test_db.commit()

    token_data = {"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role}
    refresh_token = create_refresh_token(token_data)

    result = await refresh_tokens(refresh_token, test_db)

    assert "access_token" in result
    assert "refresh_token" in result
    assert result["user"].email == test_user_data.email


@pytest.mark.asyncio
async def test_refresh_tokens_invalid_type(test_db):
    """Verify invalid token type fails refresh."""
    token_data = {"sub": "user123", "tenant_id": 1}
    access_token = create_access_token(token_data)  # Use access token instead of refresh

    with pytest.raises(HTTPException) as exc_info:
        await refresh_tokens(access_token, test_db)

    assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────────────────────
# TESTS: RBAC (Role-Based Access Control)
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_roles_assigned_correctly(test_db):
    """Verify RBAC roles are assigned based on user position."""
    owner_data = UserRegister(
        email="owner@example.com",
        password="Pass123!",
        full_name="Owner",
        tenant_name="MyCompany"
    )
    owner = await register_user(owner_data, test_db)
    assert owner.role == UserRole.OWNER

    await test_db.commit()

    analyst_data = UserRegister(
        email="analyst@example.com",
        password="Pass123!",
        full_name="Analyst",
        tenant_name="MyCompany"  # Same tenant
    )
    analyst = await register_user(analyst_data, test_db)
    assert analyst.role == UserRole.ANALYST
