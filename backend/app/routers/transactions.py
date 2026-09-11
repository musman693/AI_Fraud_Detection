"""
routers/transactions.py — Internal transaction management API.
Requires JWT auth. Role-based access enforced per endpoint.
"""
from __future__ import annotations
from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status

from app.core.dependencies import DBSession, CurrentUser, require_roles
from app.models.user import UserRole
from app.models.transaction import CSVImportJob, ImportStatus
from app.schemas.transaction import (
    TransactionCreateRequest, TransactionFilterParams,
    TransactionResponse, TransactionDetailResponse,
    PaginatedTransactionResponse, CSVImportJobResponse,
)
from app.services.transaction_service import TransactionService
from app.services.csv_import_service import parse_csv_bytes, create_import_job
from app.services.audit_service import log_action, AuditAction
from sqlalchemy import select

router = APIRouter(prefix="/transactions", tags=["Transactions (Internal)"])


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ── GET /transactions ─────────────────────────────────────────────────────────
@router.get(
    "",
    response_model=PaginatedTransactionResponse,
    summary="List transactions with search & filter",
)
async def list_transactions(
    db: DBSession,
    current_user: CurrentUser,
    customer_id: Optional[str] = Query(None),
    risk_label: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    amount_min: Optional[float] = Query(None),
    amount_max: Optional[float] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    filters = TransactionFilterParams(
        customer_id=customer_id,
        risk_label=risk_label,  # type: ignore
        decision=decision,       # type: ignore
        payment_method=payment_method,  # type: ignore
        amount_min=amount_min,
        amount_max=amount_max,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        search=search,
        page=page,
        page_size=page_size,
    )
    return await TransactionService.list_transactions(db, filters)


# ── GET /transactions/{id} ────────────────────────────────────────────────────
@router.get(
    "/{txn_id}",
    response_model=TransactionDetailResponse,
    summary="Get full transaction detail (includes decrypted PII)",
)
async def get_transaction(
    request: Request,
    txn_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    txn = await TransactionService.get_by_id(db, txn_id)
    await log_action(
        db, action=AuditAction.TRANSACTION_VIEWED,
        user_id=current_user.id,
        resource_type="transaction", resource_id=txn_id,
        ip_address=_ip(request),
    )
    return TransactionService.to_detail_response(txn)


# ── POST /transactions ────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=TransactionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually add a transaction (Admin / Business Manager)",
)
async def create_transaction(
    request: Request,
    req: TransactionCreateRequest,
    db: DBSession,
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER)),
):
    txn, _ = await TransactionService.create_transaction(
        db, req, source="manual", created_by_user_id=current_user.id
    )
    await log_action(
        db, action=AuditAction.TRANSACTION_CREATED,
        user_id=current_user.id,
        resource_type="transaction", resource_id=txn.id,
        ip_address=_ip(request),
    )
    return TransactionService.to_detail_response(txn)


# ── POST /transactions/import ─────────────────────────────────────────────────
@router.post(
    "/import",
    response_model=CSVImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk import transactions via CSV (Admin / Business Manager)",
)
async def import_csv(
    request: Request,
    file: UploadFile = File(..., description="CSV file with transaction data"),
    db: DBSession = Depends(),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER)),
):
    content = await file.read()
    df = parse_csv_bytes(content, file.filename or "upload.csv")

    job = await create_import_job(
        db, filename=file.filename or "upload.csv",
        total_rows=len(df), user_id=current_user.id,
    )

    # Enqueue Celery task with actual job.id
    from app.workers.tasks import process_csv_import
    task = process_csv_import.delay(
        job_id=str(job.id),
        csv_content_str=content.decode("utf-8", errors="replace"),
        user_id=current_user.id,
    )
    job.celery_task_id = task.id

    await log_action(
        db, action=AuditAction.CSV_IMPORT_STARTED,
        user_id=current_user.id,
        resource_type="csv_import_job", resource_id=job.id,
        extra={"filename": file.filename, "rows": len(df)},
        ip_address=_ip(request),
    )
    return CSVImportJobResponse.model_validate(job)


# ── GET /transactions/import/{job_id} ─────────────────────────────────────────
@router.get(
    "/import/{job_id}",
    response_model=CSVImportJobResponse,
    summary="Check CSV import job status",
)
async def get_import_job(job_id: str, db: DBSession, current_user: CurrentUser):
    result = await db.execute(select(CSVImportJob).where(CSVImportJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return CSVImportJobResponse.model_validate(job)


# ── DELETE /transactions/{id} ─────────────────────────────────────────────────
@router.delete(
    "/{txn_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a transaction (Admin only)",
)
async def delete_transaction(
    request: Request,
    txn_id: str,
    db: DBSession,
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    await TransactionService.soft_delete(db, txn_id)
    await log_action(
        db, action=AuditAction.TRANSACTION_DELETED,
        user_id=current_user.id,
        resource_type="transaction", resource_id=txn_id,
        ip_address=_ip(request),
    )
