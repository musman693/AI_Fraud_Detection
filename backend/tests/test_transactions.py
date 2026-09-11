"""
tests/test_transactions.py — Internal transaction endpoint tests.
"""
import io
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

VALID_TXN = {
    "customer_id": "cust_001",
    "amount": 1250.00,
    "currency": "USD",
    "payment_method": "card",
    "transaction_datetime": "2026-09-11T14:30:00Z",
    "ip_address": "192.168.1.1",
    "account_age_days": 180,
    "previous_transaction_count": 24,
}


class TestCreateTransaction:
    async def test_admin_creates_transaction(self, client: AsyncClient, admin_headers):
        resp = await client.post("/transactions", json=VALID_TXN, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["customer_id"] == "cust_001"
        assert data["amount"] == 1250.00
        assert "risk_score" in data
        assert "decision" in data

    async def test_analyst_cannot_create_transaction(self, client: AsyncClient, analyst_headers):
        resp = await client.post("/transactions", json=VALID_TXN, headers=analyst_headers)
        assert resp.status_code == 403

    async def test_invalid_amount_rejected(self, client: AsyncClient, admin_headers):
        bad = {**VALID_TXN, "amount": -100}
        resp = await client.post("/transactions", json=bad, headers=admin_headers)
        assert resp.status_code == 422

    async def test_missing_required_fields(self, client: AsyncClient, admin_headers):
        resp = await client.post("/transactions", json={"amount": 500}, headers=admin_headers)
        assert resp.status_code == 422


class TestListTransactions:
    async def test_list_returns_paginated(self, client: AsyncClient, admin_headers):
        # Create a couple of transactions first
        for i in range(3):
            await client.post(
                "/transactions",
                json={**VALID_TXN, "customer_id": f"cust_list_{i}"},
                headers=admin_headers,
            )

        resp = await client.get("/transactions?page=1&page_size=10", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)

    async def test_filter_by_customer_id(self, client: AsyncClient, admin_headers):
        await client.post(
            "/transactions",
            json={**VALID_TXN, "customer_id": "filter_cust_unique"},
            headers=admin_headers,
        )
        resp = await client.get(
            "/transactions?customer_id=filter_cust_unique", headers=admin_headers
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(t["customer_id"] == "filter_cust_unique" for t in items)

    async def test_unauthenticated_rejected(self, client: AsyncClient):
        resp = await client.get("/transactions")
        assert resp.status_code == 401


class TestGetTransaction:
    async def test_get_detail_includes_pii(self, client: AsyncClient, admin_headers):
        create = await client.post("/transactions", json=VALID_TXN, headers=admin_headers)
        txn_id = create.json()["id"]

        resp = await client.get(f"/transactions/{txn_id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ip_address"] == "192.168.1.1"   # PII decrypted

    async def test_not_found(self, client: AsyncClient, admin_headers):
        resp = await client.get(
            "/transactions/00000000-0000-0000-0000-000000000000", headers=admin_headers
        )
        assert resp.status_code == 404


class TestDeleteTransaction:
    async def test_admin_soft_deletes(self, client: AsyncClient, admin_headers):
        create = await client.post("/transactions", json=VALID_TXN, headers=admin_headers)
        txn_id = create.json()["id"]

        del_resp = await client.delete(f"/transactions/{txn_id}", headers=admin_headers)
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/transactions/{txn_id}", headers=admin_headers)
        assert get_resp.status_code == 404   # soft-deleted → not found

    async def test_analyst_cannot_delete(self, client: AsyncClient, admin_headers, analyst_headers):
        create = await client.post("/transactions", json=VALID_TXN, headers=admin_headers)
        txn_id = create.json()["id"]

        resp = await client.delete(f"/transactions/{txn_id}", headers=analyst_headers)
        assert resp.status_code == 403


class TestCSVImport:
    def _make_csv(self) -> bytes:
        lines = [
            "customer_id,amount,currency,payment_method,transaction_datetime",
            "cust_csv_1,500.00,USD,card,2026-09-01T10:00:00",
            "cust_csv_2,1200.00,USD,bank_transfer,2026-09-02T11:00:00",
        ]
        return "\n".join(lines).encode()

    async def test_csv_import_accepted(self, client: AsyncClient, admin_headers):
        csv_bytes = self._make_csv()
        resp = await client.post(
            "/transactions/import",
            headers=admin_headers,
            files={"file": ("transactions.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] in ("pending", "processing")

    async def test_csv_missing_required_column(self, client: AsyncClient, admin_headers):
        bad_csv = b"customer_id,amount\ncust1,500"
        resp = await client.post(
            "/transactions/import",
            headers=admin_headers,
            files={"file": ("bad.csv", io.BytesIO(bad_csv), "text/csv")},
        )
        assert resp.status_code == 422
