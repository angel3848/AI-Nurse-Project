# AI Nurse Project

## Identity
Digital nurse platform providing patient triage, symptom checking, BMI/health metrics, and medication reminders. Built with FastAPI + PostgreSQL.

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL 15+
- **Task Queue:** Celery + Redis
- **Auth:** OAuth2 + JWT
- **Testing:** pytest, pytest-cov

## Project Structure
```
app/
├── main.py              # FastAPI entry point
├── config.py            # Settings and env config
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── routers/             # API route handlers
├── services/            # Business logic layer
└── utils/               # Shared utilities (auth, validators)
tests/                   # Test suite
alembic/                 # Database migrations
docs/                    # Project documentation
```

## Commands
- **Run server:** `uvicorn app.main:app --reload`
- **Run tests:** `pytest tests/ -v --cov=app --cov-report=term-missing`
- **Run linter:** `ruff check app/ tests/`
- **Run formatter:** `ruff format app/ tests/`
- **Run type check:** `pyright app/`
- **Run migrations:** `alembic upgrade head`
- **Create migration:** `alembic revision --autogenerate -m "description"`

## Development Workflow

### Phase 1 — Research First (Mandatory)
Before writing new code:
1. Search PyPI for existing packages that solve the problem
2. Check FastAPI docs and community patterns
3. Look for proven implementations before writing from scratch

### Phase 2 — Plan
- Design the approach before coding
- Identify affected files, schemas, and endpoints
- Consider edge cases and error states

### Phase 3 — TDD
- Write failing test first (RED)
- Implement minimally to pass (GREEN)
- Refactor and clean up (IMPROVE)
- Target 80%+ test coverage

### Phase 4 — Review & Commit
- Run the full verification loop before committing
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

## Coding Standards

### Python Style
- **File size:** 200-400 lines typical, 800 max
- **Functions:** Under 50 lines each
- **Nesting:** Max 4 levels deep
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **No hardcoded values:** Use config.py or environment variables
- **Comments:** Explain "why", not "what"
- **Type hints:** Required on all function signatures
- **Imports:** stdlib → third-party → local, separated by blank lines

### Error Handling
- Use FastAPI HTTPException with appropriate status codes
- Comprehensive try-catch in service layer
- User-friendly error messages in API responses
- Detailed server-side logging for debugging
- Input validation via Pydantic schemas at all API boundaries

### API Design
- RESTful conventions: nouns for resources, HTTP verbs for actions
- Version prefix: `/api/v1/`
- Consistent error response format across all endpoints
- Pagination on all list endpoints (limit/offset)

### Database
- All schema changes via Alembic migrations — never modify DB directly
- Use SQLAlchemy ORM models, not raw SQL
- Index frequently queried columns
- Use UUIDs for primary keys

### Security (Mandatory Pre-Commit Checks)
- No hardcoded secrets, API keys, or credentials
- All user input validated via Pydantic schemas
- Parameterized queries only (enforced by SQLAlchemy ORM)
- JWT tokens for authentication, role-based access for authorization
- No sensitive data in error messages or logs
- CORS restricted to allowed origins

## Verification Loop (Run Before Every PR)
1. **Format:** `ruff format app/ tests/`
2. **Lint:** `ruff check app/ tests/`
3. **Type check:** `pyright app/`
4. **Tests:** `pytest tests/ -v --cov=app`
5. **Security scan:** Search for API keys, secrets, `print()` statements
6. **Diff review:** Check for unintended changes

## Git Rules
- Never bypass hooks (`--no-verify`)
- No direct commits to main — use feature branches
- Conventional commit format: `<type>: <description>`
- PR must include test plan and pass all checks before merge
