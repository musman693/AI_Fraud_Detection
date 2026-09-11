"""
schemas/transaction.py — Pydantic schemas for transactions and the risk pipeline.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Any
from datetime import datetime

from app.models.transaction import PaymentMethod, RiskLabel, DecisionStatus, TransactionStatus, ImportStatus


# ── Nested schemas ────────────────────────────────────────────────────────────

class LocationSchema(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DeviceInfoSchema(BaseModel):
    device_id: Optional[str] = None
    device_type: Optional[str] = None          # mobile | desktop | tablet
    os: Optional[str] = None
    browser: Optional[str] = None
    user_agent: Optional[str] = None
    is_new_device: Optional[bool] = None


# ── Request schemas ───────────────────────────────────────────────────────────

class TransactionCreateRequest(BaseModel):
    """Used for manual entry (internal) and external API submission."""
    customer_id: str = Field(..., min_length=1, max_length=100)
    external_transaction_id: Optional[str] = Field(None, max_length=255)
    amount: float = Field(..., gt=0, description="Transaction amount in specified currency")
    currency: str = Field("USD", min_length=3, max_length=3)
    payment_method: PaymentMethod = PaymentMethod.CARD
    transaction_datetime: datetime
    ip_address: Optional[str] = Field(None, max_length=45)
    device_info: Optional[DeviceInfoSchema] = None
    location: Optional[LocationSchema] = None
    account_age_days: Optional[int] = Field(None, ge=0)
    previous_transaction_count: Optional[int] = Field(None, ge=0)
    merchant_id: Optional[str] = Field(None, max_length=100)
    merchant_category: Optional[str] = Field(None, max_length=100)

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "cust_001",
                "amount": 1250.00,
                "currency": "USD",
                "payment_method": "card",
                "transaction_datetime": "2026-09-11T14:30:00Z",
                "ip_address": "192.168.1.1",
                "device_info": {"device_type": "mobile", "is_new_device": True},
                "location": {"country": "PK", "city": "Karachi"},
                "account_age_days": 180,
                "previous_transaction_count": 24,
            }
        }
    }


class TransactionFilterParams(BaseModel):
    """Query parameters for listing/filtering transactions."""
    customer_id: Optional[str] = None
    risk_label: Optional[RiskLabel] = None
    decision: Optional[DecisionStatus] = None
    payment_method: Optional[PaymentMethod] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None   # free-text search on customer_id / external_transaction_id
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class RiskCheckRequest(BaseModel):
    """One-shot risk check — does NOT persist the transaction."""
    customer_id: str
    amount: float = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    payment_method: PaymentMethod = PaymentMethod.CARD
    ip_address: Optional[str] = None
    device_info: Optional[DeviceInfoSchema] = None
    location: Optional[LocationSchema] = None
    account_age_days: Optional[int] = None
    previous_transaction_count: Optional[int] = None


# ── Response schemas ──────────────────────────────────────────────────────────

class RiskResponse(BaseModel):
    """Standard risk pipeline output — used by both internal and external APIs."""
    transaction_id: Optional[str] = None   # None for risk-check (not persisted)
    risk_score: float = Field(..., ge=0, le=100)
    risk_label: RiskLabel
    decision: DecisionStatus
    explanation: Optional[str] = None
    rule_flags: Optional[dict] = None
    ml_anomaly_score: Optional[float] = None
    processing_time_ms: Optional[float] = None
    timestamp: datetime


class TransactionResponse(BaseModel):
    id: str
    customer_id: str
    external_transaction_id: Optional[str]
    amount: float
    currency: str
    payment_method: PaymentMethod
    transaction_datetime: datetime
    merchant_id: Optional[str]
    merchant_category: Optional[str]
    account_age_days: Optional[int]
    previous_transaction_count: Optional[int]
    risk_score: Optional[float]
    risk_label: Optional[RiskLabel]
    decision: DecisionStatus
    risk_explanation: Optional[str]
    rule_flags: Optional[dict]
    ml_anomaly_score: Optional[float]
    source: str
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionDetailResponse(TransactionResponse):
    """Full detail view — includes decrypted PII for authorised users."""
    ip_address: Optional[str] = None
    device_info: Optional[dict] = None
    location: Optional[dict] = None
    pipeline_metadata: Optional[dict] = None


class PaginatedTransactionResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CSVImportJobResponse(BaseModel):
    job_id: str
    status: ImportStatus
    filename: str
    total_rows: Optional[int]
    processed_rows: int
    failed_rows: int
    error_log: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}
