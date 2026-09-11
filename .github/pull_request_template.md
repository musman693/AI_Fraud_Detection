## Description
<!-- Provide a concise summary of the changes introduced by this pull request. -->

## Type of Change
- [ ] 🚀 New feature (non-breaking change adding functionality)
- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] 🔒 Security fix
- [ ] ⚡ Performance improvement
- [ ] ♻️ Refactoring / Code cleanup
- [ ] 📝 Documentation update
- [ ] 🧪 Tests (adding or updating test cases)

## Module / Area
- [x] Module 1: Auth, Transaction Management & Ingestion APIs (Shayan)
- [ ] Module 2: Feature Engineering & ML Pipeline
- [ ] Module 3: Customer History & Risk Profiling
- [ ] Module 4: Fraud Detection Engine & Real-time Scoring
- [ ] Module 5: Admin Dashboard & Analytics

## Key Changes
- <!-- Bullet points of major architectural or code additions -->

## Security & Privacy Checklist
- [ ] No plaintext PII or card numbers are logged or exposed.
- [ ] Sensitive database fields use encryption (`Fernet`).
- [ ] Endpoints enforce appropriate authentication and RBAC permissions.
- [ ] Secrets and keys are loaded via environment variables (`.env`).

## How Has This Been Tested?
- [ ] Pytest test suite (`pytest tests/`)
- [ ] Manual verification via Swagger UI (`/docs`)
- [ ] Docker containerized verification (`docker-compose up`)

## GitHub Copilot / Peer Review Notes
<!-- Mention specific areas where GitHub Copilot or peer reviewer focus is requested -->
