"""
main.py — FastAPI application factory for Module 1.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routers.auth import router as auth_router
from app.routers.transactions import router as transactions_router
from app.routers.external import router as external_router, limiter


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: dispose connection pool
    await engine.dispose()


# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## AI Fraud & Risk Detection Platform — Module 1

**Module 1** provides:
- 🔐 JWT authentication with role-based access control (Admin, Business Manager, Analyst)
- 💳 Full transaction management: create, import (CSV), search/filter, detail view
- 🌐 External-facing transaction API for business partners
- ⚡ Real-time fraud detection pipeline integration
- 📋 Immutable audit logging

**Authentication:**
- Internal dashboard: `Authorization: Bearer <access_token>`
- External API: `X-API-Key: sk_<your_key>`
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Rate limiting ──────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── CORS ───────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Security headers middleware ────────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(transactions_router)
    app.include_router(external_router)

    # ── Health check ───────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Health check")
    async def health_check():
        return {
            "status": "healthy",
            "service": "module1-auth-transactions",
            "version": settings.APP_VERSION,
        }

    return app


app = create_app()
