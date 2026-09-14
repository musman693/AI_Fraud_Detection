from app.schemas.risk import TransactionPayload

ACTIVE_RULES = {
    "R001": {"name": "High Value Transaction", "amount_limit": 5000.0, "weight": 40},
    "R002": {"name": "Rapid Velocity (5 min)", "velocity_limit": 5, "weight": 50},
    "R003": {"name": "New Account High Amount", "account_age_min": 7, "amount_limit": 1000.0, "weight": 35}
}

def evaluate_rules(tx: TransactionPayload) -> tuple[float, list[str]]:
    triggered_reasons = []
    rule_score = 0.0

    if tx.amount > ACTIVE_RULES["R001"]["amount_limit"]:
        rule_score += ACTIVE_RULES["R001"]["weight"]
        triggered_reasons.append(f"Transaction amount (${tx.amount}) exceeds high threshold (${ACTIVE_RULES['R001']['amount_limit']}).")

    if tx.recent_tx_count_5min >= ACTIVE_RULES["R002"]["velocity_limit"]:
        rule_score += ACTIVE_RULES["R002"]["weight"]
        triggered_reasons.append(f"High velocity detected: {tx.recent_tx_count_5min} transactions in last 5 minutes.")

    if tx.account_age_days < ACTIVE_RULES["R003"]["account_age_min"] and tx.amount > ACTIVE_RULES["R003"]["amount_limit"]:
        rule_score += ACTIVE_RULES["R003"]["weight"]
        triggered_reasons.append(f"New account ({tx.account_age_days} days old) attempted high-value purchase (${tx.amount}).")

    return min(100.0, rule_score), triggered_reasons