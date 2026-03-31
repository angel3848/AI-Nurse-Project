# Architecture

## System Overview

```
┌─────────────────┐     ┌──────────────────────────────────────────────────────────┐
│     Clients     │     │                   AI Nurse Backend                        │
│                 │     │                                                           │
│  Browser (PWA)  │────▶│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  Mobile App     │     │  │  FastAPI    │──│  Services   │──│    PostgreSQL    │   │
│  API consumers  │◀────│  │  Routers   │  │  (Logic)    │  │   (SQLAlchemy)   │   │
│                 │     │  └────────────┘  └────────────┘  └──────────────────┘   │
│                 │     │       │    │            │                                 │
└─────────────────┘     │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │
        │               │  │   Nginx    │  │   Celery   │──│      Redis       │   │
        │               │  │   (TLS)    │  │  Workers   │  │  (Task Queue)    │   │
    WebSocket           │  └────────────┘  └────────────┘  └──────────────────┘   │
        │               │       │                                                  │
        ▼               │  ┌────────────┐  ┌────────────┐                         │
┌─────────────────┐     │  │ Middleware  │  │  Claude AI │                         │
│  /ws/triage-    │     │  │ Correlation │  │  (Optional)│                         │
│   queue         │◀────│  │ ID + CORS  │  └────────────┘                         │
└─────────────────┘     └──────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### API Layer (Routers)
- HTTP request/response handling
- Input validation via Pydantic schemas
- Authentication (JWT from cookies or Bearer token)
- Authorization (role-based + ownership checks)
- Route definitions and OpenAPI documentation
- WebSocket endpoint for real-time triage queue updates
- Rate limiting on sensitive endpoints (auth)

### Middleware Layer
- **CorrelationIDMiddleware** -- Assigns a unique `X-Correlation-ID` to every request/response cycle for distributed tracing
- **CORSMiddleware** -- Restricts cross-origin requests to configured `ALLOWED_ORIGINS`
- **Rate limiting** -- slowapi on auth endpoints

### Service Layer
- Pure business logic with no HTTP or DB dependencies
- **Triage engine:** multi-factor assessment (vitals, symptoms, pain, age modifiers)
- **Symptom checker:** 100+ condition matching with set intersection scoring
- **AI analyzer:** Optional Claude API integration for enhanced symptom analysis
- **BMI calculator:** calculation, categorization, and healthy weight range (metric + imperial)
- **Vitals assessor:** clinical range evaluation for each vital sign
- **Patient service:** aggregates patient history across triage, symptoms, and vitals
- **Medication scheduler:** CRUD for reminders with status management
- **Audit logger:** action tracking for HIPAA compliance

### Data Layer (Models + Schemas)
- SQLAlchemy 2.0 ORM models with `Mapped` type annotations
- UUID primary keys on all tables
- User <-> Patient linked via `user_id` foreign key
- Patient model uses `is_deleted` flag for soft delete
- Allergies stored as JSON array (`list[str]`), not plain string
- Cascade delete on patient relationships (medications, triage records, symptom checks, vitals)
- Vitals assessments stored immutably at write time (medical history cannot be retroactively changed)
- User model includes lockout fields (`failed_login_attempts`, `locked_until`) and reset token fields (`password_reset_token`, `reset_token_expires`)
- Alembic migrations for all schema changes
- Pydantic schemas for request validation and response serialization
- Configurable connection pooling (`pool_size`, `max_overflow`, `pool_pre_ping`)

### Task Layer (Celery Workers)
- Medication reminder scheduling and dispatch
- Email notifications via aiosmtplib
- Automatic expiration of past-due reminders
- Module-level session factory (shared engine, not per-task)

### Frontend Layer
- Jinja2 HTML templates served from FastAPI
- Mobile-first responsive design
- Patient management UI (CRUD, search, history)
- Service worker (`static/sw.js`) for offline-capable PWA:
  - Cache-first strategy for app shell assets
  - Push notification support
  - Notification click handling

## Data Flow

### Triage Assessment
1. Authenticated user submits symptoms, vitals, and patient info via `POST /api/v1/triage`
2. Router validates input against Pydantic `TriageRequest` schema
3. Triage engine evaluates: vitals -> symptoms -> pain -> age modifier -> `min()` of all levels
4. Priority level (1-5) assigned with label, color, recommended action, and flags
5. If `patient_id` provided, record persisted to `triage_records` table
6. WebSocket broadcast (`queue_updated` event) sent to all connected clients
7. Patient appears in triage queue at assigned priority

### Symptom Check (with optional AI Analysis)
1. Authenticated user submits symptoms via `POST /api/v1/symptoms/check`
2. Symptom checker matches symptoms against condition database using set intersection
3. Conditions ranked by match score, top 5 returned with probability levels
4. Urgency determined by: emergency conditions -> category -> severity -> duration -> age
5. If `AI_ANALYSIS_ENABLED=true` and `ANTHROPIC_API_KEY` is set:
   - Rule-based results are sent to Claude API for additional clinical analysis
   - AI response is included in `ai_analysis` field
   - If the AI call fails, the response continues without it (graceful degradation)
6. If `patient_id` provided, results persisted to `symptom_check_records` table

### Vitals Recording
1. Nurse/doctor submits vitals via `POST /api/v1/metrics/vitals`
2. Vitals assessor evaluates each reading against clinical ranges
3. Assessments serialized to JSON and **stored with the record** (immutable)
4. On history retrieval, stored assessments are returned directly (not recomputed)
5. Audit log entry created with user identity and IP address

### Medication Reminder
1. Nurse/doctor creates reminder via `POST /api/v1/medications/reminders`
2. Reminder schedule stored in database with times, dates, and instructions
3. Reminders can be updated via `PUT /api/v1/medications/reminders/{id}` (dosage, frequency, times, instructions, end_date)
4. Celery beat triggers `check_and_send_reminders` every 5 minutes
5. Worker checks active reminders due within current 5-minute window
6. Matching reminders dispatched via `send_reminder_notification` task
7. Patient's email found via `user_id` FK on Patient model (not name matching)

### Authentication Flow
1. User registers via `POST /api/v1/auth/register` (always patient role)
   - Password validated for complexity (uppercase, lowercase, digit, min 8 chars)
2. User authenticates via `POST /api/v1/auth/login`
   - Failed attempts tracked; account locked after 5 failures for 15 minutes
3. Server returns JWT token and sets httpOnly cookie
4. Client sends token via cookie (automatic) or `Authorization: Bearer <token>` header
5. `get_current_user` dependency extracts token, validates, checks blacklist, and loads user from DB
6. `require_role()` dependency factory checks user role for authorization
7. Ownership checks on patient endpoints ensure patients only access their own records
8. On logout, token is added to in-memory blacklist

### Password Reset Flow
1. User requests reset via `POST /api/v1/auth/forgot-password` (rate-limited)
2. If email exists, a `password_reset_token` is generated and stored with 30-minute expiry
3. Response always returns 200 (prevents user enumeration)
4. User submits token + new password via `POST /api/v1/auth/reset-password`
5. Token validated, password updated, token cleared

### WebSocket (Real-Time Triage Queue)
1. Client connects to `ws://host/ws/triage-queue?token=optional-jwt`
2. `QueueConnectionManager` tracks all active connections
3. When a triage record is created or its status is updated, `_notify_queue_updated()` broadcasts `{"event": "queue_updated"}` to all connected clients
4. Stale connections are automatically removed on send failure
5. Client should re-fetch the triage queue via REST API on receiving the event

### Patient Self-Registration
1. Patient-role user calls `POST /api/v1/patients/me`
2. System checks for existing patient record linked to the user
3. If no record exists, creates one with `user_id` set to the authenticated user's ID
4. Returns 409 if a record already exists

## Role Permissions

| Action | Patient | Nurse | Doctor | Admin |
|--------|---------|-------|--------|-------|
| Register/login | Yes | Yes | Yes | Yes |
| Forgot/reset password | Yes | Yes | Yes | Yes |
| Self-register patient profile | Yes | -- | -- | -- |
| Check symptoms | Yes | Yes | Yes | -- |
| Calculate BMI | Yes | Yes | Yes | Yes |
| View own patient record | Yes | -- | -- | -- |
| Create patient records | -- | Yes | Yes | Yes |
| View any patient record | -- | Yes | Yes | Yes |
| List/search all patients | -- | Yes | Yes | Yes |
| Submit triage | Yes | Yes | Yes | -- |
| View triage queue | -- | Yes | Yes | Yes |
| Update triage status | -- | Yes | Yes | Yes |
| Record vitals | -- | Yes | Yes | -- |
| Create medication reminders | -- | Yes | Yes | -- |
| Update medication reminders | -- | Yes | Yes | -- |
| Cancel medication reminders | -- | Yes | Yes | -- |
| View audit logs | -- | -- | -- | Yes |
| Manage users | -- | -- | -- | Yes |
| Soft-delete patients | -- | -- | -- | Yes |

## Security Architecture

- **Authentication:** JWT tokens (HS256) with configurable expiry, dual delivery (cookie + header)
- **Token blacklist:** In-memory set; tokens blacklisted on logout and user deactivation
- **Password storage:** bcrypt with auto-generated salt
- **Password complexity:** Minimum 8 characters, requires uppercase, lowercase, and digit
- **Account lockout:** 5 failed login attempts triggers a 15-minute lockout (HTTP 423)
- **Password reset:** Time-limited tokens (30 minutes), always-200 response to prevent enumeration
- **CSRF protection:** `X-Requested-With` header requirement for state-changing requests
- **Rate limiting:** slowapi on auth endpoints (5/min register, 10/min login, 5/min forgot-password)
- **Input validation:** Pydantic schemas at every API boundary
- **SQL injection:** prevented by SQLAlchemy ORM (parameterized queries)
- **CORS:** restricted to configured origins via `ALLOWED_ORIGINS`
- **Soft delete:** Patient records are never physically deleted; `is_deleted` flag preserves data
- **Ownership checks:** Patients can only access their own records (enforced per-endpoint)
- **Correlation IDs:** Every response includes `X-Correlation-ID` header for request tracing
- **Secrets:** production fail-fast if `JWT_SECRET_KEY` is unset; dev auto-generates random key
- **Container:** non-root user in Dockerfile
- **TLS:** Nginx with TLS 1.2+, HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff
- **Audit trail:** all CRUD operations on patients, vitals, and users logged with user ID and IP
- **CI security:** bandit static analysis scan in GitHub Actions pipeline

## Database Schema (Key Models)

### User
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (string 36) | Primary key |
| email | String(255) | Unique, indexed |
| hashed_password | String(255) | bcrypt |
| full_name | String(200) | |
| role | String(20) | patient, nurse, doctor, admin |
| is_active | Boolean | Default true |
| failed_login_attempts | Integer | Default 0 |
| locked_until | DateTime | Nullable |
| password_reset_token | String(255) | Nullable |
| reset_token_expires | DateTime | Nullable |
| created_at | DateTime | Server default |

### Patient
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (string 36) | Primary key |
| user_id | String(36) | FK to users.id, nullable, indexed |
| full_name | String(200) | Indexed |
| date_of_birth | Date | |
| gender | String(20) | male, female, other |
| blood_type | String(5) | Nullable |
| height_cm | Float | Nullable |
| weight_kg | Float | Nullable |
| allergies | JSON | Array of strings, nullable |
| emergency_contact_name | String(200) | Nullable |
| emergency_contact_phone | String(20) | Nullable |
| is_deleted | Boolean | Default false (soft delete) |
| created_at | DateTime | Server default |
| updated_at | DateTime | Server default, auto-updates |

Relationships: `medications`, `triage_records`, `symptom_checks`, `vitals_records` (all with `cascade="all, delete-orphan"`)

## Connection Pooling

Configurable via environment variables (ignored for SQLite):

| Setting | Default | Description |
|---------|---------|-------------|
| `POOL_SIZE` | 5 | Number of persistent connections in the pool |
| `MAX_OVERFLOW` | 10 | Additional connections beyond pool_size |
| `POOL_PRE_PING` | true | Test connections before use (handles stale connections) |
