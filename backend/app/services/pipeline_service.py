"""
services/pipeline_service.py
-----------------------------
Orchestrates the real-time fraud detection pipeline:

  [1] Data Validation
  [2] Rule Engine      → Module 2 (Sultan) — stub until ready
  [3] ML/AI Analysis   → Module 2 (Sultan) — stub until ready
  [4] Customer History → Module 3 (Noor)   — stub until ready
  [5] Risk Score Composition
  [6] Decision (Approve / Review / Alert)
  [7] (Caller responsibility) Persist + trigger alerts

Each inter-service call is wrapped with tenacity retry + fallback so
Module 1 stays healthy if Module 2 or 3 is unavailable.
"""
from __future__ import annotations
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from app.core.config import settings
from app.models.transaction import RiskLabel, DecisionStatus
from app.schemas.transaction import TransactionCreateRequest, RiskCheckRequest, RiskResponse

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_risk_label(score: float) -> RiskLabel:
    if score <= 30:
        return RiskLabel.LOW
    if score <= 70:
        return RiskLabel.MEDIUM
    return RiskLabel.HIGH


def _compute_decision(score: float) -> DecisionStatus:
    if score <= 30:
        return DecisionStatus.APPROVE
    if score <= 70:
        return DecisionStatus.REVIEW
    return DecisionStatus.ALERT


# ── Module 2 stub / real call ─────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.1, max=1))
async def _call_rule_engine(payload: dict) -> dict:
    """Call Sultan's Rule Engine endpoint."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{settings.MODULE2_BASE_URL}/internal/rule-check", json=payload)
        resp.raise_for_status()
        return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.1, max=1))
async def _call_ml_analysis(payload: dict) -> dict:
    """Call Sultan's ML Anomaly endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{settings.MODULE2_BASE_URL}/internal/ml-analysis", json=payload)
        resp.raise_for_status()
        return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.1, max=1))
async def _call_customer_history(customer_id: str) -> dict:
    """Call Noor's Customer History endpoint."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.MODULE3_BASE_URL}/internal/customers/{customer_id}/history"
        )
        resp.raise_for_status()
        return resp.json()


# ── Stub fallbacks ────────────────────────────────────────────────────────────

def _stub_rule_result(amount: float, account_age_days: Optional[int]) -> dict:
    """Heuristic stub when Module 2 Rule Engine is unavailable."""
    rule_score = 0.0
    flags: dict[str, bool] = {}

    if amount > 10_000:
        rule_score += 30
        flags["high_amount"] = True
    if amount > 50_000:
        rule_score += 20
        flags["very_high_amount"] = True
    if account_age_days is not None and account_age_days < 30:
        rule_score += 20
        flags["new_account"] = True

    return {"rule_score": min(rule_score, 50), "flags": flags}


def _stub_ml_result(amount: float) -> dict:
    """Minimal stub anomaly score — biased by amount."""
    anomaly_score = min((amount / 5000) * 40, 40)
    return {"anomaly_score": anomaly_score, "explanation": "ML module not yet available (stub)"}


def _stub_customer_history() -> dict:
    return {"avg_amount": None, "transaction_count": 0, "risk_history_score": 0}


# ── Main pipeline ──────────────────────────────────────────────────────────────

async def run_detection_pipeline(
    transaction_data: TransactionCreateRequest | RiskCheckRequest,
    transaction_id: Optional[str] = None,
) -> RiskResponse:
    """
    Run the full detection pipeline and return a RiskResponse.
    Does NOT touch the database — that's the caller's job.
    """
    t_start = time.perf_counter()

    payload = transaction_data.model_dump(mode="json")

    # [2] Rule Engine
    try:
        rule_result = await _call_rule_engine(payload)
    except (RetryError, httpx.HTTPError, Exception) as exc:
        logger.warning("Rule engine unavailable (%s) — using stub", exc)
        rule_result = _stub_rule_result(
            transaction_data.amount, transaction_data.account_age_days
        )

    # [3] ML/AI Analysis
    try:
        ml_result = await _call_ml_analysis(payload)
    except (RetryError, httpx.HTTPError, Exception) as exc:
        logger.warning("ML analysis unavailable (%s) — using stub", exc)
        ml_result = _stub_ml_result(transaction_data.amount)

    # [4] Customer History
    try:
        customer_history = await _call_customer_history(transaction_data.customer_id)
    except (RetryError, httpx.HTTPError, Exception) as exc:
        logger.warning("Customer history unavailable (%s) — using stub", exc)
        customer_history = _stub_customer_history()

    # [5] Risk Score Composition
    rule_score: float = float(rule_result.get("rule_score", 0))
    ml_score: float = float(ml_result.get("anomaly_score", 0))
    history_score: float = float(customer_history.get("risk_history_score", 0))

    # Weighted composite: 40% ML, 40% Rules, 20% history
    composite_score = round(ml_score * 0.4 + rule_score * 0.4 + history_score * 0.2, 2)
    composite_score = max(0.0, min(100.0, composite_score))

    risk_label = _compute_risk_label(composite_score)
    decision = _compute_decision(composite_score)

    # [6] Build explanation
    explanation_parts = []
    flags: dict = rule_result.get("flags", {})
    if flags.get("high_amount"):
        explanation_parts.append("Transaction amount is unusually high")
    if flags.get("new_account"):
        explanation_parts.append("Account is less than 30 days old")
    if ml_score > 30:
        explanation_parts.append(ml_result.get("explanation", "ML anomaly detected"))
    explanation = "; ".join(explanation_parts) if explanation_parts else "Transaction appears normal"

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return RiskResponse(
        transaction_id=transaction_id,
        risk_score=composite_score,
        risk_label=risk_label,
        decision=decision,
        explanation=explanation,
        rule_flags=flags,
        ml_anomaly_score=ml_score,
        processing_time_ms=elapsed_ms,
        timestamp=datetime.now(timezone.utc),
    )
