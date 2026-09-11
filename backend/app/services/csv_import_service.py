"""
services/csv_import_service.py
--------------------------------
Validates and parses CSV files. The actual DB insertion runs as a Celery task
(workers/tasks.py) so the HTTP response is immediate.
"""
from __future__ import annotations
import io
import json
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.transaction import CSVImportJob, Transaction, ImportStatus
from app.schemas.transaction import TransactionCreateRequest

# ── Required CSV columns (flexible — extras are ignored) ──────────────────────
REQUIRED_COLUMNS = {"customer_id", "amount", "currency", "payment_method", "transaction_datetime"}

COLUMN_DTYPE_MAP = {
    "customer_id": str,
    "amount": float,
    "currency": str,
    "payment_method": str,
    "transaction_datetime": str,
    "ip_address": str,
    "account_age_days": "Int64",
    "previous_transaction_count": "Int64",
    "merchant_id": str,
    "merchant_category": str,
}


def validate_csv_headers(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV missing required columns: {missing}",
        )


def parse_csv_bytes(content: bytes, filename: str) -> pd.DataFrame:
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse CSV: {exc}",
        )

    if len(df) > settings.CSV_MAX_ROWS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"CSV exceeds maximum allowed rows ({settings.CSV_MAX_ROWS})",
        )

    validate_csv_headers(df)
    return df


async def create_import_job(
    db: AsyncSession, filename: str, total_rows: int, user_id: str, celery_task_id: Optional[str] = None
) -> CSVImportJob:
    job = CSVImportJob(
        created_by_user_id=user_id,
        filename=filename,
        total_rows=total_rows,
        status=ImportStatus.PENDING,
        celery_task_id=celery_task_id,
    )
    db.add(job)
    await db.flush()
    return job


def row_to_create_request(row: dict) -> Optional[TransactionCreateRequest]:
    """Convert a CSV row dict → TransactionCreateRequest. Returns None on parse error."""
    try:
        return TransactionCreateRequest(
            customer_id=str(row["customer_id"]),
            amount=float(row["amount"]),
            currency=str(row.get("currency", "USD")),
            payment_method=row.get("payment_method", "card"),
            transaction_datetime=datetime.fromisoformat(str(row["transaction_datetime"])),
            ip_address=row.get("ip_address") or None,
            account_age_days=int(row["account_age_days"]) if row.get("account_age_days") else None,
            previous_transaction_count=int(row["previous_transaction_count"]) if row.get("previous_transaction_count") else None,
            merchant_id=row.get("merchant_id") or None,
            merchant_category=row.get("merchant_category") or None,
        )
    except Exception:
        return None
