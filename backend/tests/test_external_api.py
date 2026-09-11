"""
tests/test_external_api.py — External-facing API endpoint tests.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.models.user import APIKey, UserRole
from app.core.security import generate_api_key

pytestmark = pytest.mark.asyncio

VALID_TXN = {
    "customer_id": "ext_cust_001",
    "amount": 500.00,
    "currency": "USD",
    "payment_method": "card",
    "transaction_datetime": "2026-09-11T14:30:00Z",
    "account_age_days": 90,
}

VALID_RISK_CHECK = {
    "customer_id": "ext_cust_001",
    "amount": 250.00,
    "currency": "USD",
    "payment_method": "card",
}


@pytest.fixture
async def api_key_fixture(db, admin_user):
    """Create a real APIKey row and return the raw key."""
    raw_key, key_hash = generate_api_key()
    api_key = APIKey(name="Test Client", key_hash=key_hash, owner_id=admin_user.id)
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return raw_key, api_key


@pytest.fixture
def ext_headers(api_key_fixture):
    raw_key, _ = api_key_fixture
    return {"X-API-Key": raw_key}


class TestSubmitTransaction:
    async def test_submit_returns_risk_response(self, client: AsyncClient, ext_headers):
        resp = await client.post("/api/transactions", json=VALID_TXN, headers=ext_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "risk_score" in data
        assert 0 <= data["risk_score"] <= 100
        assert data["risk_label"] in ("low", "medium", "high")
        assert data["decision"] in ("approve", "review", "alert")
        assert "explanation" in data

    async def test_no_api_key_rejected(self, client: AsyncClient):
        resp = await client.post("/api/transactions", json=VALID_TXN)
        assert resp.status_code == 401

    async def test_invalid_api_key_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/transactions", json=VALID_TXN, headers={"X-API-Key": "sk_invalid"}
        )
        assert resp.status_code == 401

    async def test_invalid_payload_rejected(self, client: AsyncClient, ext_headers):
        resp = await client.post(
            "/api/transactions",
            json={"customer_id": "x", "amount": -10},
            headers=ext_headers,
        )
        assert resp.status_code == 422


class TestGetExternalTransaction:
    async def test_can_retrieve_own_transaction(self, client: AsyncClient, ext_headers):
        submit = await client.post("/api/transactions", json=VALID_TXN, headers=ext_headers)
        assert submit.status_code == 201

        txn_id = submit.json()["transaction_id"]
        resp = await client.get(f"/api/transactions/{txn_id}", headers=ext_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == txn_id

    async def test_cannot_access_others_transaction(
        self, client: AsyncClient, ext_headers, db, admin_user
    ):
        # Create a second API key
        raw2, hash2 = generate_api_key()
        key2 = APIKey(name="Other Client", key_hash=hash2, owner_id=admin_user.id)
        db.add(key2)
        await db.commit()

        # Submit with first key
        submit = await client.post("/api/transactions", json=VALID_TXN, headers=ext_headers)
        txn_id = submit.json()["transaction_id"]

        # Try to fetch with second key
        resp = await client.get(
            f"/api/transactions/{txn_id}", headers={"X-API-Key": raw2}
        )
        assert resp.status_code == 403


class TestRiskCheck:
    async def test_risk_check_returns_score_without_storing(
        self, client: AsyncClient, ext_headers
    ):
        resp = await client.post("/api/risk-check", json=VALID_RISK_CHECK, headers=ext_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_score" in data
        assert data.get("transaction_id") is None   # NOT persisted

    async def test_risk_check_score_in_range(self, client: AsyncClient, ext_headers):
        resp = await client.post("/api/risk-check", json=VALID_RISK_CHECK, headers=ext_headers)
        assert 0 <= resp.json()["risk_score"] <= 100

    async def test_high_amount_trends_higher_score(self, client: AsyncClient, ext_headers):
        low = await client.post(
            "/api/risk-check", json={**VALID_RISK_CHECK, "amount": 10}, headers=ext_headers
        )
        high = await client.post(
            "/api/risk-check", json={**VALID_RISK_CHECK, "amount": 100_000}, headers=ext_headers
        )
        assert high.json()["risk_score"] >= low.json()["risk_score"]
