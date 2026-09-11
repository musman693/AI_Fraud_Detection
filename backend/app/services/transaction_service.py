"""
services/transaction_service.py
CRUD and search logic for transactions.
PII fields are encrypted before write and decrypted on detail read.
"""
from __future__ import annotations
import json
import math
from typing import Optional
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import load_only

from app.models.transaction import Transaction, DecisionStatus, RiskLabel, TransactionStatus
from app.schemas.transaction import (
    TransactionCreateRequest, TransactionFilterParams,
    RiskResponse, PaginatedTransactionResponse, TransactionResponse, TransactionDetailResponse,
)
from app.core.security import encrypt_field, decrypt_field
from app.services.pipeline_service import run_detection_pipeline


class TransactionService:

    # ── Create ────────────────────────────────────────────────────────────────

    @staticmethod
    async def create_transaction(
        db: AsyncSession,
        req: TransactionCreateRequest,
        source: str = "manual",
        created_by_user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        run_pipeline: bool = True,
    ) -> tuple[Transaction, RiskResponse]:
        """
        Persist a transaction and optionally run the detection pipeline.
        Returns (transaction, risk_response).
        """
        # Encrypt PII
        ip_enc = encrypt_field(req.ip_address) if req.ip_address else None
        device_enc = encrypt_field(json.dumps(req.device_info.model_dump())) if req.device_info else None
        location_enc = encrypt_field(json.dumps(req.location.model_dump())) if req.location else None

        txn = Transaction(
            customer_id=req.customer_id,
            external_transaction_id=req.external_transaction_id,
            amount=req.amount,
            currency=req.currency.upper(),
            payment_method=req.payment_method,
            transaction_datetime=req.transaction_datetime,
            ip_address_enc=ip_enc,
            device_info_enc=device_enc,
            location_enc=location_enc,
            account_age_days=req.account_age_days,
            previous_transaction_count=req.previous_transaction_count,
            merchant_id=req.merchant_id,
            merchant_category=req.merchant_category,
            source=source,
            created_by_user_id=created_by_user_id,
            api_key_id=api_key_id,
        )
        db.add(txn)
        await db.flush()   # get id before pipeline call

        risk_response: Optional[RiskResponse] = None

        if run_pipeline:
            risk_response = await run_detection_pipeline(req, transaction_id=txn.id)
            txn.risk_score = risk_response.risk_score
            txn.risk_label = risk_response.risk_label
            txn.decision = risk_response.decision
            txn.risk_explanation = risk_response.explanation
            txn.rule_flags = risk_response.rule_flags
            txn.ml_anomaly_score = risk_response.ml_anomaly_score
            txn.pipeline_metadata = {"processing_time_ms": risk_response.processing_time_ms}

        return txn, risk_response  # type: ignore

    # ── Read ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_by_id(db: AsyncSession, txn_id: str) -> Transaction:
        result = await db.execute(
            select(Transaction).where(
                Transaction.id == txn_id,
                Transaction.status == TransactionStatus.ACTIVE,
            )
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        return txn

    @staticmethod
    def to_detail_response(txn: Transaction) -> TransactionDetailResponse:
        """Decrypt PII and return full detail."""
        data = TransactionDetailResponse.model_validate(txn)
        data.ip_address = decrypt_field(txn.ip_address_enc) if txn.ip_address_enc else None
        data.device_info = json.loads(decrypt_field(txn.device_info_enc)) if txn.device_info_enc else None
        data.location = json.loads(decrypt_field(txn.location_enc)) if txn.location_enc else None
        return data

    # ── List / Filter / Paginate ──────────────────────────────────────────────

    @staticmethod
    async def list_transactions(
        db: AsyncSession, filters: TransactionFilterParams
    ) -> PaginatedTransactionResponse:
        conditions = [Transaction.status == TransactionStatus.ACTIVE]

        if filters.customer_id:
            conditions.append(Transaction.customer_id == filters.customer_id)
        if filters.risk_label:
            conditions.append(Transaction.risk_label == filters.risk_label)
        if filters.decision:
            conditions.append(Transaction.decision == filters.decision)
        if filters.payment_method:
            conditions.append(Transaction.payment_method == filters.payment_method)
        if filters.amount_min is not None:
            conditions.append(Transaction.amount >= filters.amount_min)
        if filters.amount_max is not None:
            conditions.append(Transaction.amount <= filters.amount_max)
        if filters.date_from:
            conditions.append(Transaction.transaction_datetime >= filters.date_from)
        if filters.date_to:
            conditions.append(Transaction.transaction_datetime <= filters.date_to)
        if filters.search:
            conditions.append(
                or_(
                    Transaction.customer_id.ilike(f"%{filters.search}%"),
                    Transaction.external_transaction_id.ilike(f"%{filters.search}%"),
                )
            )

        where_clause = and_(*conditions)

        # Count
        count_result = await db.execute(select(func.count()).select_from(Transaction).where(where_clause))
        total = count_result.scalar_one()

        # Paginate
        offset = (filters.page - 1) * filters.page_size
        result = await db.execute(
            select(Transaction)
            .where(where_clause)
            .order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(filters.page_size)
        )
        items = result.scalars().all()

        return PaginatedTransactionResponse(
            items=[TransactionResponse.model_validate(t) for t in items],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=math.ceil(total / filters.page_size) if total else 0,
        )

    # ── Soft Delete ───────────────────────────────────────────────────────────

    @staticmethod
    async def soft_delete(db: AsyncSession, txn_id: str) -> None:
        txn = await TransactionService.get_by_id(db, txn_id)
        txn.status = TransactionStatus.DELETED
