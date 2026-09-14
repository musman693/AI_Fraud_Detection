from app.schemas.risk import TransactionPayload, RiskDecisionResponse
from app.services.ml_engine import predict_anomaly_score
from app.services.rules_engine import evaluate_rules

def calculate_risk_and_decision(tx: TransactionPayload) -> RiskDecisionResponse:
    ml_score = predict_anomaly_score(tx.amount, tx.account_age_days, tx.recent_tx_count_5min)
    rule_score, rule_reasons = evaluate_rules(tx)

    behavior_reasons = []
    behavior_score = 0.0
    if tx.historical_avg_amount > 0 and tx.amount > (tx.historical_avg_amount * 3):
        behavior_score += 40.0
        behavior_reasons.append(f"Customer normally spends ~${tx.historical_avg_amount}, current transaction is ${tx.amount}.")

    final_score = int(min(100.0, (ml_score * 0.3) + (rule_score * 0.5) + (behavior_score * 0.2)))

    if final_score <= 30:
        level = "Low"
        decision = "Approve"
    elif final_score <= 70:
        level = "Medium"
        decision = "Review"
    else:
        level = "High"
        decision = "Alert"

    all_explanations = rule_reasons + behavior_reasons
    if not all_explanations:
        all_explanations.append("Transaction matches normal behavior and passing rule filters.")

    return RiskDecisionResponse(
        transaction_id=tx.transaction_id,
        risk_score=final_score,
        risk_level=level,
        decision=decision,
        ml_anomaly_score=ml_score,
        rule_score=rule_score,
        explanations=all_explanations
    )