# AI Nurse Project

A digital nurse assistant that provides patient triage, symptom checking, BMI/health metric calculations, and medication reminders. Built with FastAPI and clinical decision logic based on the Australasian Triage Scale (ATS/CTAS).

## Features

- **Patient Triage** — Assess symptoms and vitals to assign 5-level priority (Resuscitation through Non-Urgent) using clinical decision rules
- **Symptom Checker** — Match reported symptoms against 100+ conditions across 12 medical categories with urgency assessment
- **BMI & Health Metrics** — Calculate BMI, record and track patient vitals with real-time assessments
- **Medication Reminders** — Schedule medication reminders with dosage, timing, and delivery via Celery + Redis
- **Patient Records** — Store and retrieve patient health data, visit history, and audit trails
- **Role-Based Access** — Four roles (patient, nurse, doctor, admin) with granular permissions
- **HIPAA-Aware** — Audit logging on all sensitive operations, ownership-based access control

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI |
| Database | PostgreSQL 15+ (SQLite for dev) |
| ORM | SQLAlchemy 2.0, Alembic migrations |
| Auth | OAuth2 + JWT (httpOnly cookies + Bearer tokens) |
| Task Queue | Celery + Redis |
| Security | bcrypt, rate limiting, CORS, TLS (nginx) |
| Testing | pytest (249 tests, 98% coverage) |
| CI/CD | GitHub Actions |
| Linting | ruff |

## Quick Start

### Local Development (SQLite)

```bash
git clone https://github.com/angel3848/AI-Nurse-Project.git
cd AI-Nurse-Project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- **http://localhost:8000** — Web UI (mobile-first)
- **http://localhost:8000/docs** — Interactive Swagger API docs

### Docker (Full Stack)

```bash
docker-compose up --build
```

This starts PostgreSQL, Redis, Celery workers, and Nginx with TLS.

## Demo Accounts

After starting the server, register via the UI or API. All registrations default to the `patient` role. To create elevated accounts, use the admin user management endpoints or update roles directly in the database.

| Role | Capabilities |
|------|-------------|
| Patient | Check symptoms, calculate BMI, view own records |
| Nurse | All patient actions + create patients, record vitals, submit triage, view queue, manage medications |
| Doctor | Same as nurse |
| Admin | All actions + manage users (roles, activate/deactivate) |

## Project Structure

```
AI_Nurse_Project/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Settings (env-based)
│   ├── database.py              # SQLAlchemy engine and session
│   ├── celery_app.py            # Celery configuration
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── user.py              # User accounts and roles
│   │   ├── patient.py           # Patient demographics (linked to User via FK)
│   │   ├── medication.py        # Medication reminders
│   │   ├── triage.py            # Triage + symptom check records
│   │   ├── vitals.py            # Vitals records (with stored assessments)
│   │   └── audit.py             # Audit log entries
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── routers/                 # API route handlers
│   │   ├── auth.py              # Register, login, logout, user management
│   │   ├── patients.py          # CRUD + history
│   │   ├── triage.py            # Triage submission + queue
│   │   ├── symptoms.py          # Symptom checker
│   │   ├── metrics.py           # BMI + vitals
│   │   ├── medications.py       # Medication reminders
│   │   └── audit.py             # Audit log access
│   ├── services/                # Business logic (no HTTP/DB dependencies)
│   │   ├── triage_engine.py     # Multi-factor triage assessment
│   │   ├── symptom_checker.py   # 100+ condition matching engine
│   │   ├── bmi_calculator.py    # BMI calculation and interpretation
│   │   ├── vitals_assessor.py   # Vital sign assessment ranges
│   │   ├── medication_scheduler.py
│   │   ├── notifier.py          # Email notification builder
│   │   └── audit_logger.py      # Audit trail service
│   ├── tasks/                   # Celery background tasks
│   │   └── reminders.py         # Medication reminder dispatch
│   └── utils/
│       ├── auth.py              # JWT, password hashing, RBAC
│       └── validators.py
├── tests/                       # 249 tests (pytest)
├── alembic/                     # Database migrations
├── templates/                   # Jinja2 HTML templates
├── static/                      # CSS, JS, images
├── nginx/                       # Nginx + TLS config
├── docs/                        # Documentation
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API Endpoints

All endpoints are prefixed with `/api/v1`. Protected endpoints require a JWT token via `Authorization: Bearer <token>` header or httpOnly cookie.

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Register (always patient role) |
| POST | `/auth/login` | No | Login, receive JWT |
| POST | `/auth/logout` | No | Clear auth cookie |
| GET | `/auth/me` | Yes | Get current user profile |
| GET | `/auth/users` | Admin | List all users |
| PUT | `/auth/users/{id}/role` | Admin | Change user role |
| PUT | `/auth/users/{id}/deactivate` | Admin | Deactivate user |
| PUT | `/auth/users/{id}/activate` | Admin | Reactivate user |

### Patients

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/patients` | Nurse/Doctor/Admin | Create patient record |
| GET | `/patients` | Nurse/Doctor/Admin | List patients (paginated) |
| GET | `/patients/{id}` | Owner or Staff | Get patient details |
| PUT | `/patients/{id}` | Nurse/Doctor/Admin | Update patient |
| DELETE | `/patients/{id}` | Admin | Delete patient |
| GET | `/patients/{id}/history` | Owner or Staff | Get visit history (triage, symptoms, vitals) |

### Triage

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/triage` | Yes | Submit triage assessment |
| GET | `/triage/queue` | Nurse/Doctor/Admin | View triage queue by priority |
| PUT | `/triage/{id}/status` | Nurse/Doctor/Admin | Update triage status |

### Symptoms

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/symptoms/check` | Yes | Analyze symptoms, get condition matches |
| GET | `/symptoms/conditions` | No | List all known conditions |

### Health Metrics

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/metrics/bmi` | No | Calculate BMI |
| POST | `/metrics/vitals` | Nurse/Doctor | Record patient vitals |
| GET | `/metrics/vitals/{patient_id}` | Yes | Get vitals history |

### Medications

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/medications/reminders` | Nurse/Doctor | Create medication reminder |
| GET | `/medications/patient/{patient_id}` | Yes | List patient medications |
| DELETE | `/medications/reminders/{id}` | Nurse/Doctor | Cancel a reminder |

## Triage Priority Levels

| Level | Label | Color | Response Time | Examples |
|-------|-------|-------|--------------|---------|
| 1 | Resuscitation | Red | Immediate | Cardiac arrest, respiratory failure |
| 2 | Emergency | Orange | 10 min | Chest pain, stroke symptoms, severe allergic reaction |
| 3 | Urgent | Yellow | 30 min | Fractures, high fever, moderate breathing difficulty |
| 4 | Semi-Urgent | Green | 60 min | Earache, minor wounds, urinary symptoms |
| 5 | Non-Urgent | Blue | 120 min | Cold symptoms, chronic follow-up, minor rash |

## Development

### Commands

```bash
# Run server
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v --cov=app --cov-report=term-missing

# Lint
ruff check app/ tests/

# Format
ruff format app/ tests/

# Run migrations
alembic upgrade head

# Create migration
alembic revision --autogenerate -m "description"
```

### Workflow

1. **Research** — Check for existing packages/patterns before writing from scratch
2. **Plan** — Design approach, identify affected files and edge cases
3. **TDD** — Write failing test, implement minimally, refactor
4. **Review** — Run full verification loop (format, lint, test, security scan)
5. **Commit** — Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

### Security Checklist

- No hardcoded secrets (enforced: production fails if JWT_SECRET_KEY unset)
- All input validated via Pydantic schemas
- Parameterized queries via SQLAlchemy ORM
- JWT with httpOnly cookies + Bearer token fallback
- Rate limiting on auth endpoints (5/min register, 10/min login)
- Role-based access control on all protected endpoints
- Patient ownership checks (patients can only view their own records)
- Audit logging on all sensitive operations
- Non-root Docker container
- Nginx with TLS 1.2+, HSTS, X-Frame-Options DENY

## Documentation

- [API Reference](docs/api_reference.md) — Full endpoint documentation with request/response examples
- [Architecture](docs/architecture.md) — System design, data flows, and role permissions
- [Deployment Guide](docs/deployment.md) — Local, Docker, and production deployment
- [Triage Guide](docs/triage_guide.md) — Clinical decision logic and priority levels

## License

MIT License. See [LICENSE](LICENSE) for details.
