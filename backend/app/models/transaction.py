"""
transaction.py — Transaction ORM model.
Sensitive PII fields (ip_address, device_info, location) are stored encrypted.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Index,
    Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaymentMethod(str, PyEnum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"
    MOBILE_MONEY = "mobile_money"
    OTHER = "other"


class RiskLabel(str, PyEnum):
    LOW = "low"        # 0-30
    MEDIUM = "medium"  # 31-70
    HIGH = "high"      # 71-100


class DecisionStatus(str, PyEnum):
    APPROVE = "approve"
    REVIEW = "review"
    ALERT = "alert"
    PENDING = "pending"


class TransactionStatus(str, PyEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class ImportStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transaction(Base):
    __tablename__ = "transactions"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Customer / business context ───────────────────────────────────────────
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )  # ID from the submitting business system

    # ── Financial ─────────────────────────────────────────────────────────────
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod), nullable=False, default=PaymentMethod.CARD
    )

    # ── Timing ────────────────────────────────────────────────────────────────
    transaction_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # ── PII fields (stored Fernet-encrypted) ─────────────────────────────────
    ip_address_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_info_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # encrypted JSON
    location_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # encrypted JSON

    # ── Non-sensitive context ─────────────────────────────────────────────────
    account_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    previous_transaction_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    merchant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    merchant_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Risk & Decision (filled by pipeline) ─────────────────────────────────
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_label: Mapped[Optional[RiskLabel]] = mapped_column(Enum(RiskLabel), nullable=True, index=True)
    decision: Mapped[DecisionStatus] = mapped_column(
        Enum(DecisionStatus), nullable=False, default=DecisionStatus.PENDING, index=True
    )
    risk_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_flags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)       # which rules fired
    ml_anomaly_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pipeline_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ── Source / admin ────────────────────────────────────────────────────────
    source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="api"
    )  # "api" | "manual" | "csv_import"
    api_key_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("api_keys.id"), nullable=True
    )
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), nullable=False, default=TransactionStatus.ACTIVE
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    api_key: Mapped[Optional["APIKey"]] = relationship("APIKey", lazy="noload")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_txn_customer_datetime", "customer_id", "transaction_datetime"),
        Index("ix_txn_risk_score", "risk_score"),
        Index("ix_txn_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.id} | {self.amount} {self.currency} | {self.decision}>"


class CSVImportJob(Base):
    """Tracks async CSV import jobs."""
    __tablename__ = "csv_import_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus), nullable=False, default=ImportStatus.PENDING
    )
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
