"""
services/auth_service.py
Business logic for authentication and user/API-key management.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
import redis.asyncio as aioredis
import logging
import time

from app.models.user import User, APIKey, UserRole
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token, get_jti,
    generate_api_key,
)
from app.core.config import settings
from app.schemas.auth import UserCreateRequest, LoginRequest

logger = logging.getLogger(__name__)


class AuthService:

    # ── User management ───────────────────────────────────────────────────────

    @staticmethod
    async def create_user(db: AsyncSession, req: UserCreateRequest) -> User:
        # Check duplicate email
        existing = await db.execute(select(User).where(User.email == req.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = User(
            email=req.email,
            hashed_password=hash_password(req.password),
            full_name=req.full_name,
            role=req.role,
        )
        db.add(user)
        await db.flush()   # get generated id without committing
        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        return result.scalar_one_or_none()

    # ── Authentication ────────────────────────────────────────────────────────

    @staticmethod
    async def authenticate(db: AsyncSession, req: LoginRequest) -> tuple[User, str, str]:
        """Returns (user, access_token, refresh_token) or raises HTTPException."""
        result = await db.execute(select(User).where(User.email == req.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

        access_token = create_access_token(user.id, user.role.value)
        refresh_token = create_refresh_token(user.id)
        return user, access_token, refresh_token

    @staticmethod
    async def refresh_access_token(
        db: AsyncSession, redis: aioredis.Redis, refresh_token: str
    ) -> tuple[str, str]:
        """
        Rotate refresh token — invalidate old one, return new pair.
        
        Implements atomic refresh token revocation using Redis SET NX.
        This prevents race conditions where both an attacker and legitimate user
        can refresh simultaneously.
        """
        from jose import JWTError
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        jti = payload.get("jti", "")
        if await redis.exists(f"blacklist:{jti}"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

        user_id = payload["sub"]
        result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # ── Atomic refresh token revocation (race condition protection) ────────
        # Use Redis SET NX (set if not exists) to ensure only one refresh succeeds
        exp_timestamp = payload.get("exp", 0)
        ttl = max(int(exp_timestamp - time.time()), 1)
        
        # Atomically set revocation record. If it already exists, token was already used.
        revocation_key = f"blacklist:{jti}"
        was_set = await redis.set(revocation_key, "1", ex=ttl, nx=True)
        
        if not was_set:
            # Key already existed - another process already revoked this token
            logger.warning("Refresh token replay attempt detected (JTI: %s)", jti)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token already used",
            )

        new_access = create_access_token(user.id, user.role.value)
        new_refresh = create_refresh_token(user.id)
        return new_access, new_refresh

    @staticmethod
    async def logout(redis: aioredis.Redis, access_token: str, refresh_token: Optional[str] = None) -> None:
        """Blacklist the access token (and optionally the refresh token)."""
        from jose import JWTError

        for token in filter(None, [access_token, refresh_token]):
            try:
                payload = decode_token(token)
                jti = payload.get("jti", "")
                exp = payload.get("exp", 0)
                ttl = max(int(exp - time.time()), 1)
                await redis.setex(f"blacklist:{jti}", ttl, "1")
                logger.info("Token blacklisted (JTI: %s)", jti)
            except JWTError as e:
                logger.warning("Failed to blacklist token: %s", type(e).__name__)
                pass   # token already invalid — fine

    # ── API Keys ──────────────────────────────────────────────────────────────

    @staticmethod
    async def create_api_key(
        db: AsyncSession,
        name: str,
        owner_id: str,
        expires_in_days: Optional[int] = None,
    ) -> tuple[APIKey, str]:
        """
        Returns (api_key_obj, raw_key).
        Store raw_key — it's shown only once.
        
        If expires_in_days is None, uses default from config.
        If default is None, key never expires.
        """
        raw_key, key_hash = generate_api_key()
        
        expires_at = None
        if expires_in_days is None:
            expires_in_days = settings.API_KEY_DEFAULT_EXPIRATION_DAYS
        
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        api_key = APIKey(
            name=name,
            key_hash=key_hash,
            owner_id=owner_id,
            expires_at=expires_at,
        )
        db.add(api_key)
        await db.flush()
        return api_key, raw_key

    @staticmethod
    async def revoke_api_key(db: AsyncSession, key_id: str, owner_id: str) -> None:
        result = await db.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.owner_id == owner_id)
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        api_key.is_active = False
        logger.info("API key revoked: %s", key_id)
