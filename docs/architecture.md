# Architecture

## System Overview

```
┌─────────────┐     ┌─────────────────────────────────────────────┐
│   Clients   │     │              AI Nurse Backend                │
│             │     │                                             │
│  Patients   │────▶│  ┌─────────┐  ┌──────────┐  ┌───────────┐ │
│  Nurses     │     │  │ FastAPI  │──│ Services  │──│ Database  │ │
│  Doctors    │◀────│  │ Routers  │  │ (Logic)   │  │ (Postgres)│ │
│  Hospitals  │     │  └─────────┘  └──────────┘  └───────────┘ │
│             │     │                     │                       │
└─────────────┘     │              ┌──────────┐                   │
                    │              │  Celery   │──▶ Redis          │
                    │              │  Workers  │   (Task Queue)    │
                    │              └──────────┘                   │
                    └─────────────────────────────────────────────┘
```

## Layer Responsibilities

### API Layer (Routers)
- HTTP request/response handling
- Input validation via Pydantic schemas
- Authentication and authorization checks
- Route definitions and OpenAPI documentation

### Service Layer
- Core business logic
- Triage decision engine
- Symptom analysis algorithms
- BMI and health metric calculations
- Medication scheduling logic

### Data Layer (Models)
- SQLAlchemy ORM models
- Database schema definitions
- Alembic migrations

### Task Layer (Celery Workers)
- Asynchronous medication reminder delivery
- Scheduled health check notifications
- Background data processing

## Data Flow

### Triage Assessment
1. Patient or nurse submits symptoms and vitals via `POST /api/v1/triage`
2. Router validates input against Pydantic schema
3. Triage engine service analyzes symptoms, vitals, and patient history
4. Priority level (1-5) is assigned based on clinical decision rules
5. Result is stored in database and returned to caller
6. Patient is placed in triage queue at appropriate priority

### Symptom Check
1. Patient submits symptoms via `POST /api/v1/symptoms/check`
2. Symptom checker service matches symptoms against condition database
3. Possible conditions are ranked by probability
4. Recommended actions are generated (self-care, see doctor, emergency)
5. Results returned with disclaimers about seeking professional care

### Medication Reminder
1. Nurse or doctor creates reminder via `POST /api/v1/medications/reminders`
2. Reminder schedule is stored in database
3. Celery beat triggers reminder tasks at scheduled times
4. Worker sends notification to patient
5. Acknowledgment is tracked for compliance monitoring

## Authentication Flow

1. User authenticates via `POST /api/v1/auth/login`
2. Server validates credentials and returns JWT access token
3. Client includes token in `Authorization: Bearer <token>` header
4. Middleware validates token and attaches user context to request
5. Route handlers check user role for authorization

## Role Permissions

| Action | Patient | Nurse | Doctor | Admin |
|--------|---------|-------|--------|-------|
| View own records | Yes | — | — | — |
| Submit symptoms | Yes | Yes | Yes | — |
| Create triage | — | Yes | Yes | Yes |
| View triage queue | — | Yes | Yes | Yes |
| Prescribe medication | — | — | Yes | — |
| Create reminders | — | Yes | Yes | — |
| View all patients | — | Yes | Yes | Yes |
| Manage users | — | — | — | Yes |
