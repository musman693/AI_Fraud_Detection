"""
tests/test_auth.py — Auth endpoint tests.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_admin_can_create_user(self, client: AsyncClient, admin_headers):
        resp = await client.post(
            "/auth/register",
            json={
                "email": "newanalyst@test.com",
                "password": "Secret1234!",
                "full_name": "New Analyst",
                "role": "analyst",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newanalyst@test.com"
        assert data["role"] == "analyst"

    async def test_analyst_cannot_create_user(self, client: AsyncClient, analyst_headers):
        resp = await client.post(
            "/auth/register",
            json={
                "email": "another@test.com",
                "password": "Secret1234!",
                "full_name": "Another",
                "role": "analyst",
            },
            headers=analyst_headers,
        )
        assert resp.status_code == 403

    async def test_duplicate_email_rejected(self, client: AsyncClient, admin_headers, admin_user):
        resp = await client.post(
            "/auth/register",
            json={
                "email": admin_user.email,
                "password": "Secret1234!",
                "full_name": "Dup",
                "role": "analyst",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 409


class TestLogin:
    async def test_valid_login(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/auth/login",
            json={"email": admin_user.email, "password": "Admin1234!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_wrong_password(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/auth/login",
            json={"email": admin_user.email, "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    async def test_unknown_email(self, client: AsyncClient):
        resp = await client.post(
            "/auth/login",
            json={"email": "ghost@nowhere.com", "password": "anything"},
        )
        assert resp.status_code == 401


class TestMe:
    async def test_get_profile(self, client: AsyncClient, admin_user, admin_headers):
        resp = await client.get("/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == admin_user.email

    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

    async def test_invalid_token(self, client: AsyncClient):
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


class TestRefresh:
    async def test_refresh_returns_new_tokens(self, client: AsyncClient, admin_user):
        login = await client.post(
            "/auth/login", json={"email": admin_user.email, "password": "Admin1234!"}
        )
        refresh_token = login.json()["refresh_token"]

        resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_invalid_refresh_token(self, client: AsyncClient):
        resp = await client.post("/auth/refresh", json={"refresh_token": "bad.token"})
        assert resp.status_code == 401
