from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AlertStatusUpdate(BaseModel):
    status: str # New, Investigating, Confirmed Fraud, False Positive, Resolved

class InvestigationNoteCreate(BaseModel):
    analyst_id: str
    notes: str

class CustomerProfileResponse(BaseModel):
    customer_id: str
    risk_level: str
    risk_score: float
    total_transactions: int
    suspicious_transactions: int
    devices_used: List[str]
    locations_used: List[str]
    previous_fraud_reports: int

class NetworkNodeResponse(BaseModel):
    nodes: List[dict]
    edges: List[dict]