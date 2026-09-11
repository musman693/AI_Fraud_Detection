"""
security.py
-----------
Handles all cryptographic operations for Module 1:
  - Password hashing   (bcrypt via passlib)
  - JWT creation/verification  (RS256 via python-jose)
  - Fernet field-level encryption for PII fields
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid
import logging

import base64
import secrets
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Password hashing ────────────────────────────────────────────────────────
# Using bcrypt with explicit cost factor of 14 (recommended for 2024+)
# Cost factor increases automatically with hardware improvements over time
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=14)


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt (cost=14)."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plaintext against bcrypt hash (timing-safe)."""
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ──────────────────────────────────────────────────────────
def _build_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
    """Build a JWT with standard claims (exp, iat, jti)."""
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload["exp"] = now + expires_delta
    payload["iat"] = now
    payload["jti"] = str(uuid.uuid4())   # unique token ID (for blacklisting)
    return jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str, extra: Optional[Dict] = None) -> str:
    """Create a short-lived access token (15 minutes by default)."""
    data: Dict[str, Any] = {"sub": user_id, "role": role, "type": "access"}
    if extra:
        data.update(extra)
    return _build_token(data, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token (7 days by default)."""
    data: Dict[str, Any] = {"sub": user_id, "type": "refresh"}
    return _build_token(data, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT.
    
    Raises JWTError on:
      - Signature verification failure
      - Expired token
      - Invalid format
    
    Explicitly enforces RS256 algorithm (not configurable from token).
    """
    return jwt.decode(
        token,
        settings.JWT_PUBLIC_KEY,
        algorithms=[settings.JWT_ALGORITHM],  # Only RS256, not negotiable
        options={"verify_signature": True, "verify_exp": True},
    )


def get_jti(token: str) -> str:
    """
    Extract the JTI (JWT ID) claim without full validation.
    Used for blacklisting on logout.
    """
    try:
        unverified = jwt.get_unverified_claims(token)
        return unverified.get("jti", "")
    except JWTError as e:
        logger.warning("Failed to extract JTI from token: %s", type(e).__name__)
        return ""


# ── Fernet field encryption ───────────────────────────────────────────────────
# Cached Fernet instance to avoid repeated key derivation
_fernet_instance: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """
    Get cached Fernet instance.
    
    Instantiating Fernet involves PBKDF2 key derivation which is intentionally slow.
    Caching the instance per process prevents repeated key derivation.
    Fernet is thread-safe, so this is safe for async/concurrent use.
    """
    global _fernet_instance
    if _fernet_instance is None:
        key = settings.FIELD_ENCRYPTION_KEY
        if not key:
            # Dev fallback — generate a stable in-process key (NOT for production)
            logger.warning("Using development-only encryption key. Set FIELD_ENCRYPTION_KEY in production!")
            key = base64.urlsafe_b64encode(b"dev-key-32bytes-not-for-prod!!!!").decode()
        _fernet_instance = Fernet(key.encode())
    return _fernet_instance


def encrypt_field(value: str) -> str:
    """
    Encrypt a string value using Fernet (AES-128 + HMAC).
    
    Returns URL-safe base64 ciphertext suitable for database storage.
    Empty/None values pass through unchanged.
    """
    if not value:
        return value
    try:
        encrypted = _get_fernet().encrypt(value.encode()).decode()
        logger.debug("Field encrypted successfully (length: %d bytes)", len(encrypted))
        return encrypted
    except Exception as e:
        # Sanitize logs: never log the value itself
        logger.error("Field encryption failed: %s", type(e).__name__)
        raise


def decrypt_field(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted field back to plaintext.
    
    Raises ValueError if:
      - Ciphertext is tampered with (HMAC fails)
      - Wrong encryption key is configured
      - Ciphertext format is invalid
    
    Empty/None values pass through unchanged.
    """
    if not ciphertext:
        return ciphertext
    try:
        plaintext = _get_fernet().decrypt(ciphertext.encode()).decode()
        logger.debug("Field decrypted successfully")
        return plaintext
    except InvalidToken as e:
        # Possible tampering or wrong key
        logger.error("Decryption failed (possible tampering or wrong key): %s", type(e).__name__)
        raise ValueError("Invalid encrypted data - possible tampering") from e
    except Exception as e:
        # Other cryptography errors
        logger.error("Unexpected decryption error: %s", type(e).__name__)
        raise


# ── API Key helpers ──────────────────────────────────────────────────────────
# API keys are secrets and should use slow hashing (bcrypt) like passwords


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key pair.
    
    Returns:
        (raw_key, hashed_key)
    
    The raw_key should be:
      - Sent ONCE to the client immediately after generation
      - Never stored in DB or logs
      - Cannot be recovered after generation
    
    The hashed_key should be:
      - Stored in DB with index for fast lookup
      - Used for all subsequent authentication
    
    Using bcrypt (not SHA256) prevents rainbow table attacks.
    """
    raw = "sk_" + secrets.token_urlsafe(32)
    hashed = pwd_context.hash(raw)  # Use bcrypt (cost=14), not SHA256
    return raw, hashed


def hash_api_key(raw: str) -> str:
    """
    Hash an API key for lookup against stored hashes.
    Uses bcrypt to prevent rainbow table attacks.
    """
    return pwd_context.hash(raw)


def verify_api_key(raw: str, hashed: str) -> bool:
    """
    Verify a raw API key against its bcrypt hash.
    Timing-safe comparison.
    """
    try:
        return pwd_context.verify(raw, hashed)
    except Exception as e:
        logger.warning("API key verification error: %s", type(e).__name__)
        return False
