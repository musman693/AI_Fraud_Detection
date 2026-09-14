from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "active"

def test_high_risk_transaction_scoring():
    payload = {
        "transaction_id": "tx_999",
        "customer_id": "cust_123",
        "amount": 7500.0,
        "ip_address": "192.168.1.1",
        "location": "Lahore, PK",
        "device_id": "dev_abc",
        "account_age_days": 2,
        "recent_tx_count_5min": 6,
        "historical_avg_amount": 50.0
    }
    res = client.post("/api/v1/risk/score", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_score"] > 70
    assert data["decision"] in ["Alert", "Review"]
    assert len(data["explanations"]) > 0