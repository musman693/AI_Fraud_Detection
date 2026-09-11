"""
services/audit_service.py
Writes immutable audit log entries. Always call fire-and-forget style.
"""
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    action: str,
    user_id: Optional[str] = None,
    api_key_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """
    Insert an audit log row.

    Usage:
        await log_action(db, action="LOGIN_SUCCESS", user_id=user.id, ip_address=request.client.host)
    """
    entry = AuditLog(
        user_id=user_id,
        api_key_id=api_key_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        extra=json.dumps(extra) if extra else None,
    )
    db.add(entry)
    # Intentionally NOT calling await db.flush() here — let the outer request
    # commit handle it so we stay in the same transaction.


# ── Common action constants ────────────────────────────────────────────────────

class AuditAction:
    # Auth
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"
    USER_CREATED = "USER_CREATED"
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"

    # Transactions
    TRANSACTION_CREATED = "TRANSACTION_CREATED"
    TRANSACTION_VIEWED = "TRANSACTION_VIEWED"
    TRANSACTION_DELETED = "TRANSACTION_DELETED"
    CSV_IMPORT_STARTED = "CSV_IMPORT_STARTED"
    CSV_IMPORT_COMPLETED = "CSV_IMPORT_COMPLETED"

    # External API
    EXTERNAL_TRANSACTION_SUBMITTED = "EXTERNAL_TRANSACTION_SUBMITTED"
    RISK_CHECK_PERFORMED = "RISK_CHECK_PERFORMED"
