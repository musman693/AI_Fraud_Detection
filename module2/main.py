from fastapi import FastAPI
from app.routers import risk

app = FastAPI(
    title="AI Fraud Detection - Module 2 Risk & Decision Engine",
    version="1.0.0",
    description="ML Anomaly Scoring, Rules Engine, AI Explanations & LLM Investigation Assistant"
)

app.include_router(risk.router, prefix="/api/v1/risk", tags=["Module 2 AI/ML Risk Scoring"])

@app.get("/")
def root():
    return {"status": "active", "service": "Module 2 Risk Engine Online"}