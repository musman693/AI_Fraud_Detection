"""
schemas/auth.py — Pydantic request/response schemas for authentication.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.user import UserRole


# ── Request schemas ───────────────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.ANALYST


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Friendly name, e.g. 'Acme Corp'")


# ── Response schemas ──────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int   # seconds until access token expires


class APIKeyResponse(BaseModel):
    id: str
    name: str
    raw_key: Optional[str] = Field(
        None,
        description="Shown ONCE at creation — store it securely. Not retrievable again.",
    )
    is_active: bool

    model_config = {"from_attributes": True}
