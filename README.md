# AI Fraud & Risk Detection Platform

> **Module 1 — Auth, Transaction Management & Ingestion APIs**  
> Owner: **Shayan** | Stack: Python · FastAPI · PostgreSQL · Redis · Celery

---

## Project Overview

A full-stack AI-powered fraud and risk detection system built by a 5-person team.

| Module | Owner | Description |
|--------|-------|-------------|
| **1 — Auth & Transactions** | **Shayan** | Auth, transaction CRUD, ingestion API, detection pipeline |
| 2 — AI/ML Risk Engine | Sultan | Risk scoring, anomaly detection, rules engine, AI explanations |
| 3 — Alerts & Reporting | Noor-ul-Ain | Alerts, investigations, customer profiles, fraud network |
| 4 — Frontend | Usman | React/Next.js dashboards, investigation UI, charts |
| 5 — QA & Docs | Nouman | Integration testing, README, weekly summaries |

---

## Module 1 — Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+

### 1. Clone and configure
```bash
git clone <repo-url>
cd AI_FRAUD_DETECTION

cp backend/.env.example backend/.env
# Edit backend/.env — fill in JWT keys and encryption key (see instructions inside)
```

### 2. Generate secrets
```bash
# JWT RS256 keys
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem

# Fernet encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Start all services
```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| FastAPI backend | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Flower (Celery) | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 4. Run database migrations
```bash
cd backend
alembic upgrade head
```

### 5. Run unit tests
```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## API Overview

### Internal API (JWT Auth)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | Admin | Create user |
| POST | `/auth/login` | Public | Get JWT tokens |
| POST | `/auth/refresh` | Public | Rotate tokens |
| POST | `/auth/logout` | Any | Invalidate tokens |
| GET | `/auth/me` | Any | Current user |
| POST | `/auth/api-keys` | Admin | Create external API key |
| DELETE | `/auth/api-keys/{id}` | Admin | Revoke API key |
| GET | `/transactions` | Any | List + filter |
| GET | `/transactions/{id}` | Any | Full detail |
| POST | `/transactions` | Admin/BM | Manual create |
| POST | `/transactions/import` | Admin/BM | CSV bulk import |
| GET | `/transactions/import/{job_id}` | Any | Import status |
| DELETE | `/transactions/{id}` | Admin | Soft delete |

### External API (X-API-Key header)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transactions` | Submit + get risk score |
| GET | `/api/transactions/{id}` | Retrieve your transaction |
| POST | `/api/risk-check` | One-shot risk check (no persistence) |

---

## Detection Pipeline

```
Incoming Transaction
  └─ [1] Data Validation (schema + business rules)
  └─ [2] Rule Engine      (Module 2 — Sultan)
  └─ [3] ML/AI Analysis   (Module 2 — Sultan)
  └─ [4] Customer History (Module 3 — Noor)
  └─ [5] Risk Score Composition (0-100)
             Low 0-30  → Approve
             Med 31-70 → Review
             High 71+  → Alert
  └─ [6] Audit Log + Alert Trigger
```

Each inter-service call has a **circuit breaker** (tenacity) — Module 1 stays online if Module 2/3 are down, using heuristic stubs.

---

## Project Structure

```
AI_FRAUD_DETECTION/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── core/
│   │   │   ├── config.py        # pydantic-settings
│   │   │   ├── security.py      # JWT, bcrypt, Fernet
│   │   │   ├── database.py      # async SQLAlchemy engine
│   │   │   └── dependencies.py  # DI: get_db, auth, RBAC
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── routers/             # FastAPI route handlers
│   │   ├── services/            # Business logic
│   │   └── workers/             # Celery tasks
│   ├── tests/                   # pytest test suite
│   ├── alembic/                 # DB migrations
│   ├── .env.example
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
└── docker-compose.yml
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Async PostgreSQL URL |
| `REDIS_URL` | Redis URL |
| `JWT_PRIVATE_KEY` | RS256 private key (PEM) |
| `JWT_PUBLIC_KEY` | RS256 public key (PEM) |
| `FIELD_ENCRYPTION_KEY` | Fernet key for PII fields |
| `MODULE2_BASE_URL` | Sultan's risk engine URL |
| `MODULE3_BASE_URL` | Noor's alerts/profiles URL |
| `EXTERNAL_API_RATE_LIMIT` | e.g. `60/minute` |

---

## Security

- **Passwords**: bcrypt (passlib)
- **JWTs**: RS256, 15-min access + 7-day refresh with Redis blacklist
- **PII encryption**: Fernet symmetric encryption at rest for ip_address, device_info, location
- **API keys**: SHA-256 hashed before DB storage
- **Rate limiting**: slowapi — 60 req/min on external API
- **Transport**: HTTPS enforced via HSTS header
- **Audit logs**: Every mutating action logged immutably

---

## Weekly Delivery

| Week | Deliverable |
|------|-------------|
| 1 | Scaffold, DB models, migrations, auth endpoints |
| 2 | Transaction CRUD + CSV import |
| 3 | External API + detection pipeline |
| 4 | Security hardening, audit logs, tests ≥85%, API docs |
