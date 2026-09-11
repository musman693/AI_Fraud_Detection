"""
routers/external.py — External-facing Transaction API.
Authenticated via X-API-Key header. Rate-limited via slowapi.
These endpoints are what outside businesses call.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import DBSession, ValidAPIKey
from app.schemas.transaction import (
    TransactionCreateRequest, RiskCheckRequest,
    TransactionDetailResponse, RiskResponse,
)
from app.services.transaction_service import TransactionService
from app.services.pipeline_service import run_detection_pipeline
from app.services.audit_service import log_action, AuditAction
from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api", tags=["External Transaction API"])


# ── POST /api/transactions ────────────────────────────────────────────────────
@router.post(
    "/transactions",
    response_model=RiskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a transaction for ingestion + real-time risk scoring",
    description="""
Submit a transaction from your system. We will:
1. Validate the payload
2. Persist the transaction
3. Run the fraud detection pipeline
4. Return a risk score (0-100), label (low/medium/high), and decision (approve/review/alert)

**Auth:** `X-API-Key` header  
**Rate limit:** 60 requests / minute per IP
""",
)
@limiter.limit(settings.EXTERNAL_API_RATE_LIMIT)
async def submit_transaction(
    request: Request,
    req: TransactionCreateRequest,
    db: DBSession,
    api_key: ValidAPIKey,
):
    txn, risk_response = await TransactionService.create_transaction(
        db, req, source="api", api_key_id=api_key.id, run_pipeline=True
    )

    # Update API key last_used
    api_key.last_used_at = datetime.now(timezone.utc)

    await log_action(
        db,
        action=AuditAction.EXTERNAL_TRANSACTION_SUBMITTED,
        api_key_id=api_key.id,
        resource_type="transaction",
        resource_id=txn.id,
        ip_address=request.client.host if request.client else None,
    )

    return risk_response


# ── GET /api/transactions/{id} ────────────────────────────────────────────────
@router.get(
    "/transactions/{txn_id}",
    response_model=TransactionDetailResponse,
    summary="Retrieve a submitted transaction and its risk score",
)
@limiter.limit(settings.EXTERNAL_API_RATE_LIMIT)
async def get_transaction(
    request: Request,
    txn_id: str,
    db: DBSession,
    api_key: ValidAPIKey,
):
    txn = await TransactionService.get_by_id(db, txn_id)

    # External clients can only see their own transactions
    if txn.api_key_id != api_key.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return TransactionService.to_detail_response(txn)


# ── POST /api/risk-check ──────────────────────────────────────────────────────
@router.post(
    "/risk-check",
    response_model=RiskResponse,
    summary="One-shot risk check — no persistence, instant score",
    description="""
Run the fraud detection pipeline on a transaction payload **without** persisting it.
Useful for pre-screening or testing.

**Auth:** `X-API-Key` header  
**Rate limit:** 60 requests / minute per IP
""",
)
@limiter.limit(settings.EXTERNAL_API_RATE_LIMIT)
async def risk_check(
    request: Request,
    req: RiskCheckRequest,
    db: DBSession,
    api_key: ValidAPIKey,
):
    api_key.last_used_at = datetime.now(timezone.utc)

    risk_response = await run_detection_pipeline(req)

    await log_action(
        db,
        action=AuditAction.RISK_CHECK_PERFORMED,
        api_key_id=api_key.id,
        ip_address=request.client.host if request.client else None,
        extra={"customer_id": req.customer_id, "amount": req.amount},
    )

    return risk_response
