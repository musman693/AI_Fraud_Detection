def test_register_and_login(client):
    resp = client.post("/api/auth/register", json={
        "name": "Test Admin", "email": "test-admin@example.com", "password": "Secret123!", "role": "ADMIN",
    })
    assert resp.status_code == 201

    resp = client.post("/api/auth/login", json={"email": "test-admin@example.com", "password": "Secret123!"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_invalid_credentials(client):
    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_development_login_bypass_creates_user(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DEV_LOGIN_BYPASS", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.delenv("TESTING", raising=False)

    resp = client.post("/api/auth/login", json={
        "email": "new-user@example.com", "password": "any-random-password",
    })

    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "new-user@example.com"
    assert resp.json()["user"]["role"] == "ANALYST"


def test_development_login_bypass_uses_demo_roles(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DEV_LOGIN_BYPASS", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.delenv("TESTING", raising=False)

    expected_roles = {
        "admin@fraudshield.ai": "ADMIN",
        "manager@fraudshield.ai": "BUSINESS_MANAGER",
        "analyst@fraudshield.ai": "ANALYST",
    }
    for email, role in expected_roles.items():
        response = client.post("/api/auth/login", json={
            "email": email, "password": "any-password",
        })

        assert response.status_code == 200
        assert response.json()["user"]["role"] == role


def test_development_login_bypass_corrects_existing_demo_role(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DEV_LOGIN_BYPASS", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.delenv("TESTING", raising=False)

    registered = client.post("/api/auth/register", json={
        "name": "Manager", "email": "manager@fraudshield.ai",
        "password": "original-password", "role": "ANALYST",
    })
    assert registered.status_code == 201

    response = client.post("/api/auth/login", json={
        "email": "manager@fraudshield.ai", "password": "any-password",
    })

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "BUSINESS_MANAGER"
