"""
routers/auth.py — Authentication and user management endpoints.
"""
from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.dependencies import DBSession, RedisClient, CurrentUser, require_roles
from app.models.user import UserRole
from app.schemas.auth import (
    UserCreateRequest, LoginRequest, RefreshRequest,
    UserResponse, TokenResponse, APIKeyCreateRequest, APIKeyResponse,
)
from app.services.auth_service import AuthService
from app.services.audit_service import log_action, AuditAction
from app.core.config import settings
from app.core.security import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ── POST /auth/register ───────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (Admin only)",
)
async def register_user(
    request: Request,
    req: UserCreateRequest,
    db: DBSession,
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    user = await AuthService.create_user(db, req)
    await log_action(
        db, action=AuditAction.USER_CREATED,
        user_id=current_user.id,
        resource_type="user", resource_id=user.id,
        ip_address=_client_ip(request),
    )
    return UserResponse.model_validate(user)


# ── POST /auth/login ──────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse, summary="Login and receive JWT tokens")
async def login(request: Request, req: LoginRequest, db: DBSession):
    try:
        user, access_token, refresh_token = await AuthService.authenticate(db, req)
        await log_action(
            db, action=AuditAction.LOGIN_SUCCESS,
            user_id=user.id, ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except HTTPException as exc:
        await log_action(
            db, action=AuditAction.LOGIN_FAILED,
            extra={"email": req.email}, ip_address=_client_ip(request),
        )
        raise


# ── POST /auth/refresh ────────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token")
async def refresh_token(req: RefreshRequest, db: DBSession, redis: RedisClient):
    new_access, new_refresh = await AuthService.refresh_access_token(db, redis, req.refresh_token)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Invalidate tokens")
async def logout(
    request: Request,
    current_user: CurrentUser,
    redis: RedisClient,
    db: DBSession,
    req: RefreshRequest,  # Now required (not optional)
):
    """
    Logout and invalidate both access and refresh tokens.
    
    Requires refresh_token in request body for security.
    This ensures the user intentionally logs out, not just sending a stale access token.
    """
    auth = request.headers.get("authorization", "")
    access_token = auth.removeprefix("Bearer ").strip()
    refresh_token = req.refresh_token

    await AuthService.logout(redis, access_token, refresh_token)
    await log_action(
        db,
        action=AuditAction.LOGOUT,
        user_id=current_user.id,
        ip_address=_client_ip(request),
    )


# ── GET /auth/me ──────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: CurrentUser):
    return UserResponse.model_validate(current_user)


# ── POST /auth/api-keys ───────────────────────────────────────────────────────
@router.post(
    "/api-keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an external API key (Admin only)",
)
async def create_api_key(
    request: Request,
    req: APIKeyCreateRequest,
    db: DBSession,
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    api_key_obj, raw_key = await AuthService.create_api_key(db, req.name, current_user.id)
    await log_action(
        db, action=AuditAction.API_KEY_CREATED,
        user_id=current_user.id,
        resource_type="api_key", resource_id=api_key_obj.id,
        ip_address=_client_ip(request),
    )
    return APIKeyResponse(id=api_key_obj.id, name=api_key_obj.name, raw_key=raw_key, is_active=True)


# ── DELETE /auth/api-keys/{id} ────────────────────────────────────────────────
@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key (Admin only)",
)
async def revoke_api_key(
    request: Request,
    key_id: str,
    db: DBSession,
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    await AuthService.revoke_api_key(db, key_id, current_user.id)
    await log_action(
        db, action=AuditAction.API_KEY_REVOKED,
        user_id=current_user.id,
        resource_type="api_key", resource_id=key_id,
        ip_address=_client_ip(request),
    )
