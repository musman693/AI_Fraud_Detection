from fastapi import APIRouter, HTTPException
from app.schemas.risk import TransactionPayload, RiskDecisionResponse, FeedbackPayload, AssistantQuery
from app.services.decision_engine import calculate_risk_and_decision
from app.services.assistant_service import query_investigation_assistant

router = APIRouter()

FEEDBACK_STORE = []

@router.post("/score", response_model=RiskDecisionResponse)
async def score_transaction(payload: TransactionPayload):
    return calculate_risk_and_decision(payload)

@router.post("/feedback")
async def record_feedback(payload: FeedbackPayload):
    FEEDBACK_STORE.append(payload.dict())
    return {"status": "success", "message": "Feedback recorded for model retrain loop."}

@router.post("/investigate-assistant")
async def investigate_assistant(payload: AssistantQuery):
    answer = await query_investigation_assistant(payload.transaction_id, payload.customer_id, payload.question)
    return {"transaction_id": payload.transaction_id, "answer": answer}