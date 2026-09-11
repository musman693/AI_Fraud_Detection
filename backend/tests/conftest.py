"""
tests/conftest.py — Shared pytest fixtures.
Uses an in-memory SQLite DB for speed (no Postgres needed for unit tests).
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.core.database import Base
from app.core.dependencies import get_db, get_redis
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token

# ── In-memory SQLite engine ────────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=0)
    redis.setex = AsyncMock(return_value=True)
    return redis


@pytest_asyncio.fixture
async def client(db, mock_redis) -> AsyncClient:
    """HTTP test client with DB and Redis overridden."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Test users ─────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def admin_user(db) -> User:
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("Admin1234!"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def analyst_user(db) -> User:
    user = User(
        email="analyst@test.com",
        hashed_password=hash_password("Analyst1234!"),
        full_name="Test Analyst",
        role=UserRole.ANALYST,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user) -> str:
    return create_access_token(admin_user.id, admin_user.role.value)


@pytest.fixture
def analyst_token(analyst_user) -> str:
    return create_access_token(analyst_user.id, analyst_user.role.value)


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def analyst_headers(analyst_token) -> dict:
    return {"Authorization": f"Bearer {analyst_token}"}
