"""
dependencies.py
---------------
FastAPI dependency injection — database session, current user, role guards,
API key authentication, Redis client.
"""
from typing import Annotated, AsyncGenerator
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token, hash_api_key
from app.core.config import settings
from app.models.user import User, APIKey, UserRole

# ── DB Session ────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DBSession = Annotated[AsyncSession, Depends(get_db)]

# ── Redis ─────────────────────────────────────────────────────────────────────
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL, db=settings.REDIS_TOKEN_BLACKLIST_DB, decode_responses=True
        )
    return _redis_client


RedisClient = Annotated[aioredis.Redis, Depends(get_redis)]

# ── JWT Auth ──────────────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    db: DBSession,
    redis: RedisClient,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> User:
    if credentials is None:
        raise _CREDENTIALS_ERROR
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise _CREDENTIALS_ERROR

    if payload.get("type") != "access":
        raise _CREDENTIALS_ERROR

    # Check token blacklist (logout)
    jti = payload.get("jti", "")
    if jti and await redis.exists(f"blacklist:{jti}"):
        raise _CREDENTIALS_ERROR

    user_id: str = payload.get("sub", "")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise _CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

# ── Role guards ───────────────────────────────────────────────────────────────
def require_roles(*roles: UserRole):
    """Factory that returns a FastAPI dependency enforcing one of the given roles."""
    async def _guard(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return _guard


def AdminOnly():
    return Depends(require_roles(UserRole.ADMIN))


def AdminOrBM():
    return Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER))


def AnyRole():
    return Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER, UserRole.ANALYST))

# ── External API Key Auth ─────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_API_KEY_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or missing API key",
)


async def get_api_key(
    db: DBSession,
    key: str | None = Security(api_key_header),
) -> APIKey:
    if not key:
        raise _API_KEY_ERROR
    hashed = hash_api_key(key)
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == hashed, APIKey.is_active == True)
    )
    api_key_obj = result.scalar_one_or_none()
    if api_key_obj is None:
        raise _API_KEY_ERROR
    return api_key_obj


ValidAPIKey = Annotated[APIKey, Depends(get_api_key)]
