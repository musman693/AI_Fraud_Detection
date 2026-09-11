# GitHub Copilot Custom Instructions for AI Fraud Detection Platform

This repository houses a high-throughput, enterprise-grade AI Fraud & Risk Detection Platform built with FastAPI, PostgreSQL, Redis, and Celery.
When generating code, conducting code reviews, or offering suggestions in this repository, you MUST adhere strictly to the following architectural, security, and quality guidelines:

---

## 1. Architectural Guidelines & Clean Separation of Concerns
- **Layered Architecture:**
  - `routers/`: HTTP request handling, route definitions, parameter validation, and dependency injection. Routers MUST NOT execute direct database queries or raw SQL.
  - `services/`: Encapsulate core business logic, orchestration, and transactional workflows.
  - `models/`: SQLAlchemy 2.0 ORM models.
  - `schemas/`: Pydantic v2 data models for input validation and serialization.
  - `workers/`: Asynchronous background task execution using Celery.
  - `core/`: Application configuration (`pydantic-settings`), database engine/session factories, security, and shared dependencies.
- **Dependency Injection:** Utilize FastAPI's `Depends()` for database sessions (`get_db`), authentication (`get_current_active_user`), role-based access control (`require_role`), and rate limiting.

---

## 2. Security & Compliance Standards (PCI-DSS & SOC2)
- **PII & Cardholder Data Protection:**
  - Card numbers MUST NEVER be stored in plaintext. Always use `EncryptionService` (Fernet symmetric encryption) for encrypted fields.
  - Plaintext card numbers or sensitive PII MUST NEVER be printed in log messages, exception tracebacks, or audit events. Use masked formats (e.g., `**** **** **** 1234`).
- **Authentication & Authorization:**
  - Passwords MUST be hashed using `bcrypt` via PassLib.
  - JWT authentication uses asymmetric RS256 with key rotation support.
  - All protected endpoints must validate token expiration, signature, and user active status.
- **Audit Logging:**
  - Security-sensitive actions (login, API key generation, manual fraud review status changes) must trigger asynchronous audit log creation via `AuditService`.

---

## 3. Database & Query Performance
- **SQLAlchemy 2.0 Syntax:** Use modern `select()`, `update()`, `delete()` syntax rather than legacy query syntax.
- **Indexing & Constraints:** Ensure high-frequency query filters (`user_id`, `status`, `timestamp`, `account_id`) have corresponding indexes and foreign key constraints with indexed columns.
- **Async & Pooling:** Ensure session lifecycle is handled cleanly via context managers or FastAPI dependency yields without session leaks.

---

## 4. Background Workers & Celery Tasks
- **Idempotency:** Background workers processing CSV ingestion or fraud evaluation must be idempotent and resilient to retries.
- **Chunked Processing:** Large datasets or CSV uploads must be ingested in batches (e.g., 500-1000 records per chunk) to avoid memory starvation.
- **Job Status Tracking:** Track job states (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) in database tables for user transparency.

---

## 5. Code Review Checklist for Copilot
When reviewing pull requests or diffs:
1. Ensure no secrets, private keys, or API tokens are hardcoded.
2. Verify all new endpoints have unit or integration test coverage with `pytest`.
3. Check for input validation and boundary checks in Pydantic schemas.
4. Confirm response models use explicit `response_model` declarations to prevent data leakage.
5. Check that error responses adhere to standard HTTP status codes (400, 401, 403, 404, 422, 500) with clear, actionable error messages.
