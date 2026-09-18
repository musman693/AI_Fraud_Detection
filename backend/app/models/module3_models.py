from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base # ya aapke project ka base model import

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    customer_id = Column(String, primary_key=True, index=True)
    risk_level = Column(String, default="LOW") # LOW, MEDIUM, HIGH
    risk_score = Column(Float, default=0.0)
    total_transactions = Column(Integer, default=0)
    suspicious_transactions = Column(Integer, default=0)
    devices_used = Column(JSON, default=[])
    locations_used = Column(JSON, default=[])
    previous_fraud_reports = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, index=True)
    customer_id = Column(String, ForeignKey("customer_profiles.customer_id"))
    reason = Column(Text)
    severity = Column(String) # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String, default="New") # New, Investigating, Confirmed Fraud, False Positive, Resolved
    created_at = Column(DateTime, default=datetime.utcnow)

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, index=True)
    customer_id = Column(String)
    analyst_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="Open")
    created_at = Column(DateTime, default=datetime.utcnow)