# Architecture

## System Overview

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│   Clients   │     │               AI Nurse Backend                   │
│             │     │                                                  │
│  Patients   │────▶│  ┌──────────┐  ┌───────────┐  ┌──────────────┐ │
│  Nurses     │     │  │ FastAPI   │──│ Services   │──│  PostgreSQL  │ │
│  Doctors    │◀────│  │ Routers   │  │ (Logic)    │  │  (SQLAlchemy)│ │
│  Admins     │     │  └──────────┘  └───────────┘  └──────────────┘ │
│             │     │       │              │                           │
└─────────────┘     │  ┌──────────┐  ┌───────────┐                   │
                    │  │  Nginx   │  │  Celery    │──▶ Redis          │
                    │  │  (TLS)   │  │  Workers   │   (Task Queue)   │
                    │  └──────────┘  └───────────┘                   │
                    └──────────────────────────────────────────────────┘
```

## Layer Responsibilities

### API Layer (Routers)
- HTTP request/response handling
- Input validation via Pydantic schemas
- Authentication (JWT from cookies or Bearer token)
- Authorization (role-based + ownership checks)
- Route definitions and OpenAPI documentation

### Service Layer
- Pure business logic with no HTTP or DB dependencies
- Triage engine: multi-factor assessment (vitals, symptoms, pain, age modifiers)
- Symptom checker: 100+ condition matching with set intersection scoring
- BMI calculator: calculation, categorization, and healthy weight range
- Vitals assessor: clinical range evaluation for each vital sign
- Audit logger: action tracking for HIPAA compliance

### Data Layer (Models + Schemas)
- SQLAlchemy 2.0 ORM models with `Mapped` type annotations
- UUID primary keys on all tables
- User ↔ Patient linked via `user_id` foreign key
- Vitals assessments stored immutably at write time (medical history cannot be retroactively changed)
- Alembic migrations for all schema changes
- Pydantic schemas for request validation and response serialization

### Task Layer (Celery Workers)
- Medication reminder scheduling and dispatch
- Email notifications via aiosmtplib
- Automatic expiration of past-due reminders
- Module-level session factory (shared engine, not per-task)

## Data Flow

### Triage Assessment
1. Authenticated user submits symptoms, vitals, and patient info via `POST /api/v1/triage`
2. Router validates input against Pydantic `TriageRequest` schema
3. Triage engine evaluates: vitals → symptoms → pain → age modifier → `min()` of all levels
4. Priority level (1-5) assigned with label, color, recommended action, and flags
5. If `patient_id` provided, record persisted to `triage_records` table
6. Patient appears in triage queue at assigned priority

### Symptom Check
1. Authenticated user submits symptoms via `POST /api/v1/symptoms/check`
2. Symptom checker matches symptoms against condition database using set intersection
3. Conditions ranked by match score, top 5 returned with probability levels
4. Urgency determined by: emergency conditions → category → severity → duration → age
5. If `patient_id` provided, results persisted to `symptom_check_records` table

### Vitals Recording
1. Nurse/doctor submits vitals via `POST /api/v1/metrics/vitals`
2. Vitals assessor evaluates each reading against clinical ranges
3. Assessments serialized to JSON and **stored with the record** (immutable)
4. On history retrieval, stored assessments are returned directly (not recomputed)
5. Audit log entry created with user identity and IP address

### Medication Reminder
1. Nurse/doctor creates reminder via `POST /api/v1/medications/reminders`
2. Reminder schedule stored in database with times, dates, and instructions
3. Celery beat triggers `check_and_send_reminders` every 5 minutes
4. Worker checks active reminders due within current 5-minute window
5. Matching reminders dispatched via `send_reminder_notification` task
6. Patient's email found via `user_id` FK on Patient model (not name matching)

### Authentication Flow
1. User registers via `POST /api/v1/auth/register` (always patient role)
2. User authenticates via `POST /api/v1/auth/login`
3. Server returns JWT token and sets httpOnly cookie
4. Client sends token via cookie (automatic) or `Authorization: Bearer <token>` header
5. `get_current_user` dependency extracts token, validates, and loads user from DB
6. `require_role()` dependency factory checks user role for authorization
7. Ownership checks on patient endpoints ensure patients only access their own records

## Role Permissions

| Action | Patient | Nurse | Doctor | Admin |
|--------|---------|-------|--------|-------|
| Register/login | Yes | Yes | Yes | Yes |
| Check symptoms | Yes | Yes | Yes | — |
| Calculate BMI | Yes | Yes | Yes | Yes |
| View own patient record | Yes | — | — | — |
| Create patient records | — | Yes | Yes | Yes |
| View any patient record | — | Yes | Yes | Yes |
| List all patients | — | Yes | Yes | Yes |
| Submit triage | Yes | Yes | Yes | — |
| View triage queue | — | Yes | Yes | Yes |
| Update triage status | — | Yes | Yes | Yes |
| Record vitals | — | Yes | Yes | — |
| Manage medications | — | Yes | Yes | — |
| View audit logs | — | — | — | Yes |
| Manage users | — | — | — | Yes |
| Delete patients | — | — | — | Yes |

## Security Architecture

- **Authentication:** JWT tokens (HS256) with configurable expiry, dual delivery (cookie + header)
- **Password storage:** bcrypt with auto-generated salt
- **Rate limiting:** slowapi on auth endpoints (5/min register, 10/min login)
- **Input validation:** Pydantic schemas at every API boundary
- **SQL injection:** prevented by SQLAlchemy ORM (parameterized queries)
- **CORS:** restricted to configured origins
- **Secrets:** production fail-fast if `JWT_SECRET_KEY` is unset; dev auto-generates random key
- **Container:** non-root user in Dockerfile
- **TLS:** Nginx with TLS 1.2+, HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff
- **Audit trail:** all CRUD operations on patients and vitals logged with user ID and IP
