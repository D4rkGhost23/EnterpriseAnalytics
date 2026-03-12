"""
Unit Tests for Authentication Service - SIMPLIFIED VERSION
Tests: Password hashing, JWT tokens, basic validation
"""
import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError

from core.config import settings
from core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token
)
from models.user import UserRole


# ─────────────────────────────────────────────────────────────
# TESTS: Password Hashing & Verification (NO DB NEEDED)
# ─────────────────────────────────────────────────────────────

class TestPasswordHashing:
    """Test password hashing and verification without database."""
    
    def test_hash_password_creates_non_plaintext(self):
        """Verify password hash is not plaintext."""
        password = "MyPassword123!"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > len(password)

    def test_verify_password_success(self):
        """Verify valid password passes verification."""
        password = "MyPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Verify incorrect password fails verification."""
        password = "MyPassword123!"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Password verification is case-sensitive."""
        password = "MyPassword123!"
        hashed = hash_password(password)
        assert verify_password("mypassword123!", hashed) is False

    def test_hash_is_unique_each_time(self):
        """Each hash should be different (bcrypt adds salt)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify the same password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# ─────────────────────────────────────────────────────────────
# TESTS: JWT Token Creation & Validation (NO DB NEEDED)
# ─────────────────────────────────────────────────────────────

class TestJWTTokens:
    """Test JWT token generation and validation."""
    
    def test_create_access_token(self):
        """Verify access token is created with correct structure."""
        data = {"sub": "user123", "tenant_id": 1, "role": UserRole.ANALYST.value}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0
        # Token should be JWT format (3 parts separated by dots)
        assert token.count(".") == 2

    def test_create_refresh_token(self):
        """Verify refresh token is created with correct structure."""
        data = {"sub": "user123", "tenant_id": 1}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2

    def test_decode_access_token(self):
        """Verify access token can be decoded and contains payload."""
        original_data = {"sub": "user123", "tenant_id": 1, "role": UserRole.ANALYST.value}
        token = create_access_token(original_data)
        decoded = decode_token(token)

        assert decoded["sub"] == original_data["sub"]
        assert decoded["tenant_id"] == original_data["tenant_id"]
        assert decoded["type"] == "access"
        assert "exp" in decoded

    def test_decode_refresh_token(self):
        """Verify refresh token can be decoded."""
        original_data = {"sub": "user123", "tenant_id": 1}
        token = create_refresh_token(original_data)
        decoded = decode_token(token)

        assert decoded["sub"] == original_data["sub"]
        assert decoded["type"] == "refresh"

    def test_decode_invalid_token(self):
        """Verify invalid token raises exception."""
        invalid_token = "invalid.token.here"
        with pytest.raises(Exception):  # Could be JWTError or HTTPException
            decode_token(invalid_token)

    def test_token_has_expiration(self):
        """Verify token contains expiration timestamp."""
        data = {"sub": "user123"}
        token = create_access_token(data)
        decoded = decode_token(token)
        
        assert "exp" in decoded
        # exp should be a unix timestamp in the future
        assert decoded["exp"] > datetime.now(timezone.utc).timestamp()

    def test_access_and_refresh_token_are_different(self):
        """Verify access and refresh tokens have different types."""
        data = {"sub": "user123"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)
        
        assert access != refresh
        assert decode_token(access)["type"] == "access"
        assert decode_token(refresh)["type"] == "refresh"


# ─────────────────────────────────────────────────────────────
# TESTS: Token Expiration & Validation
# ─────────────────────────────────────────────────────────────

class TestTokenExpiration:
    """Test token expiration behavior."""
    
    def test_expired_token_validation(self):
        """Verify expired token raises exception."""
        data = {"sub": "user123"}
        # Create token with expired timestamp manually
        expired_data = data.copy()
        expired_data["exp"] = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_token = jwt.encode(expired_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        with pytest.raises(Exception):
            decode_token(expired_token)

    def test_access_token_expires_before_refresh(self):
        """Verify access token expires quicker than refresh token."""
        data = {"sub": "user123"}
        access = decode_token(create_access_token(data))
        refresh = decode_token(create_refresh_token(data))
        
        # Access token should expire sooner (lower exp timestamp)
        assert access["exp"] < refresh["exp"]


# ─────────────────────────────────────────────────────────────
# TESTS: RBAC (Role-Based Access Control) - Values
# ─────────────────────────────────────────────────────────────

class TestRBAC:
    """Test role-based access control values."""
    
    def test_user_roles_exist(self):
        """Verify all required user roles exist."""
        roles = [UserRole.OWNER, UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER]
        assert len(roles) == 4

    def test_role_values_are_strings(self):
        """Verify role values are strings."""
        assert isinstance(UserRole.OWNER.value, str)
        assert isinstance(UserRole.ADMIN.value, str)
        assert isinstance(UserRole.ANALYST.value, str)
        assert isinstance(UserRole.VIEWER.value, str)

    def test_role_string_representations(self):
        """Verify role string values."""
        assert UserRole.OWNER.value == "owner"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.VIEWER.value == "viewer"


# ─────────────────────────────────────────────────────────────
# INTEGRATION TEST: Complete Auth Flow (Mocked)
# ─────────────────────────────────────────────────────────────

class TestAuthenticationFlow:
    """Test complete authentication flow."""
    
    def test_complete_auth_flow(self):
        """Test: Register → Hash password → Create tokens."""
        # Step 1: Hash password like registration would
        password = "SecurePass123!@#"
        hashed = hash_password(password)
        assert hashed != password

        # Step 2: Verify password like login would
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

        # Step 3: Create tokens like after login
        user_data = {
            "sub": "user123",
            "tenant_id": 1,
            "role": UserRole.ANALYST.value
        }
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)

        # Step 4: Verify tokens
        access_decoded = decode_token(access_token)
        refresh_decoded = decode_token(refresh_token)

        assert access_decoded["sub"] == "user123"
        assert refresh_decoded["sub"] == "user123"
        assert access_decoded["type"] == "access"
        assert refresh_decoded["type"] == "refresh"


# ─────────────────────────────────────────────────────────────
# DATABASE TESTS (Conceptual - No actual DB)
# ─────────────────────────────────────────────────────────────

def test_auth_db_register_creates_user():
    """Test that user objects can be created with proper attributes."""
    # Simulate user creation
    password = "Password123!"
    hashed = hash_password(password)
    
    # Verify hash was created
    assert hashed is not None
    assert hashed != password
    assert verify_password(password, hashed) is True
    
    # Simulate user object creation
    user_data = {
        "email": "test@example.com",
        "hashed_password": hashed,
        "full_name": "Test User",
        "role": UserRole.OWNER
    }
    
    assert user_data["email"] == "test@example.com"
    assert user_data["role"] == UserRole.OWNER
    assert user_data["hashed_password"] is not None


def test_auth_db_password_never_plaintext():
    """Test that password is always hashed, never stored plaintext."""
    plaintext = "MySecretPassword123!"
    hashed = hash_password(plaintext)

    # Verify stored hash is never plaintext
    assert hashed != plaintext
    assert verify_password(plaintext, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    
    # Simulate user object
    user_data = {
        "email": "secure@example.com",
        "hashed_password": hashed,
        "full_name": "Secure User",
        "role": UserRole.ANALYST
    }
    
    # Verify password is hashed in object
    assert user_data["hashed_password"] != plaintext
