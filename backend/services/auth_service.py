"""
Authentication Service – Register, Login, Refresh Token.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from fastapi import HTTPException, status
import structlog

from models.user import User, Tenant, UserRole
from schemas.auth import UserRegister, UserLogin
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

logger = structlog.get_logger()


async def register_user(data: UserRegister, db: AsyncSession) -> User:
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create or fetch tenant
    slug = data.tenant_name.lower().replace(" ", "-")
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    tenant = result.scalar_one_or_none()

    if not tenant:
        tenant = Tenant(name=data.tenant_name, slug=slug)
        db.add(tenant)
        await db.flush()  # Get tenant.id before user creation
        # First user in a new tenant is owner
        role = UserRole.OWNER
    else:
        role = UserRole.ANALYST

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=role,
        tenant_id=tenant.id,
    )
    db.add(user)
    await db.flush()
    logger.info("user_registered", email=data.email, tenant=tenant.slug, role=role)
    return user


async def login_user(data: UserLogin, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        logger.warning("login_failed", email=data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    token_data = {"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    logger.info("login_success", email=data.email, user_id=user.id)
    return {"access_token": access_token, "refresh_token": refresh_token, "user": user}


async def refresh_tokens(refresh_token: str, db: AsyncSession) -> dict:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role}
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "user": user,
    }
