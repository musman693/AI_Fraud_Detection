from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TransactionPayload(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    ip_address: str
    location: str
    device_id: str
    account_age_days: int
    recent_tx_count_5min: int = 0
    historical_avg_amount: float = 100.0

class RiskDecisionResponse(BaseModel):
    transaction_id: str
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str  # Low (0-30), Medium (31-70), High (71-100)
    decision: str    # Approve, Review, Alert
    ml_anomaly_score: float
    rule_score: float
    explanations: List[str]

class RuleConfig(BaseModel):
    rule_id: str
    name: str
    max_amount_threshold: float
    max_velocity_5min: int
    is_active: bool = True

class FeedbackPayload(BaseModel):
    transaction_id: str
    analyst_decision: str  # 'Confirmed Fraud' or 'False Positive'
    notes: Optional[str] = None

class AssistantQuery(BaseModel):
    transaction_id: str
    customer_id: str
    question: str