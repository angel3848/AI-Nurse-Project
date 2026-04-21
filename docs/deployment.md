# Deployment Guide

## Local Development (SQLite)

The fastest way to run the project. Uses SQLite -- no external services needed.

```bash
git clone https://github.com/angel3848/AI-Nurse-Project.git
cd AI-Nurse-Project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- **http://localhost:8000** -- Web UI (patient management, triage, BMI calculator)
- **http://localhost:8000/docs** -- Swagger API docs

> **Note:** Celery features (medication reminders) require Redis. WebSocket, AI analysis, and everything else work with SQLite.

### Creating Demo Accounts

Register via the UI or API:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@test.com","password":"DemoPass1","full_name":"Demo User"}'
```

> **Password requirements:** Minimum 8 characters, at least one uppercase letter, one lowercase letter, and one digit.

All registrations default to `patient` role. To create nurse/doctor/admin accounts, register them and update roles via the admin API or directly in the database.

---

## Local Development (PostgreSQL + Redis)

For full-stack development including Celery workers:

```bash
# Start PostgreSQL and Redis
docker run -d --name ai-nurse-db -p 5432:5432 \
  -e POSTGRES_DB=ai_nurse_db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  postgres:15

docker run -d --name ai-nurse-redis -p 6379:6379 redis:7

# Configure environment
cp .env.example .env
# Edit .env with your database URL and Redis URL

# Run migrations and start
source venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

### Running Celery Workers

In separate terminals (with venv activated):

```bash
# Celery worker (processes tasks)
celery -A app.celery_app worker --loglevel=info

# Celery beat (schedules periodic tasks)
celery -A app.celery_app beat --loglevel=info
```

### Enabling AI Analysis (Optional)

To enable Claude-powered symptom analysis:

```bash
# In your .env file:
AI_ANALYSIS_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

When enabled, `POST /api/v1/symptoms/check` will include an `ai_analysis` field with an AI-generated clinical analysis alongside the rule-based results. If the AI call fails, the response continues without it.

---

## Docker Compose (Full Stack)

Starts all services: API, PostgreSQL, Redis, Celery worker, Celery beat, and Nginx with TLS.

```bash
docker-compose up --build
```

The `docker-compose.yml` in the project root includes:
- **api** -- FastAPI application (non-root user, HEALTHCHECK configured)
- **db** -- PostgreSQL 15 with health checks
- **redis** -- Redis 7 with health checks
- **celery-worker** -- Background task processor (shares the `ai-nurse-api:latest` image)
- **celery-beat** -- Periodic task scheduler (shares the `ai-nurse-api:latest` image)
- **nginx** -- Reverse proxy with TLS termination

> **Image reuse:** The Docker image is built once by the `api` service and tagged as `ai-nurse-api:latest`. The `celery-worker` and `celery-beat` services reuse this image (no `version` key in compose file -- uses Compose V2 format).

### Automatic Migrations

The `entrypoint.sh` script runs `alembic upgrade head` automatically before starting the application. No manual migration step is needed after the first `docker-compose up`.

```bash
#!/bin/sh
set -e
echo "Running database migrations..."
alembic upgrade head
echo "Starting application..."
exec "$@"
```

### Health Checks

The API container includes a Docker HEALTHCHECK that polls `GET /health` every 30 seconds:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

The `docker-compose.yml` also defines service-level health checks for PostgreSQL (via `pg_isready`) and Redis (via `redis-cli ping`). The API service waits for both `db` and `redis` to be healthy before starting.

### TLS Certificates

The nginx config expects TLS certificates at:
- `nginx/certs/cert.pem`
- `nginx/certs/key.pem`

For local development, generate self-signed certs:
```bash
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/key.pem \
  -out nginx/certs/cert.pem \
  -subj "/CN=localhost"
```

For production, use Let's Encrypt or your organization's CA.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `AI Nurse` | Application name |
| `APP_VERSION` | `0.1.0` | Application version |
| `APP_ENV` | `development` | Environment (`development` or `production`) |
| `DEBUG` | `false` | Debug mode |
| `DATABASE_URL` | `sqlite:///./ai_nurse.db` | Database connection string |
| `JWT_SECRET_KEY` | Auto-generated (dev only) | **Required in production** -- fails to start if unset |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiry in minutes |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection for Celery |
| `ALLOWED_ORIGINS` | `["http://localhost:3000", "http://localhost:8000"]` | CORS allowed origins (JSON array) |
| `COOKIE_SECURE` | `false` | Set `true` in production (requires HTTPS) |
| `COOKIE_DOMAIN` | `None` | Cookie domain restriction |
| `POOL_SIZE` | `5` | Database connection pool size (ignored for SQLite) |
| `MAX_OVERFLOW` | `10` | Max additional connections beyond pool_size |
| `POOL_PRE_PING` | `true` | Test connections before use |
| `AI_ANALYSIS_ENABLED` | `false` | Enable Claude AI symptom analysis |
| `ANTHROPIC_API_KEY` | (empty) | Anthropic API key for Claude |
| `SMTP_HOST` | (empty) | SMTP server for email notifications |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | (empty) | SMTP username |
| `SMTP_PASSWORD` | (empty) | SMTP password |
| `SMTP_FROM_EMAIL` | `noreply@ainurse.local` | Sender email address |
| `SMTP_FROM_NAME` | `AI Nurse` | Sender display name |
| `NOTIFICATION_ENABLED` | `false` | Enable email sending |

---

## Production Deployment

### Security Checklist

- [ ] Set a strong, unique `JWT_SECRET_KEY` (never use the auto-generated dev key)
- [ ] Set `APP_ENV=production` (enforces `JWT_SECRET_KEY` requirement)
- [ ] Set `COOKIE_SECURE=true` (requires HTTPS)
- [ ] Restrict `ALLOWED_ORIGINS` to your frontend domain(s)
- [ ] Use environment variables for all secrets -- never commit `.env` files
- [ ] Enable TLS via nginx or a cloud load balancer
- [ ] Review rate limiting configuration for your expected load
- [ ] Set strong passwords (minimum 8 chars, uppercase, lowercase, digit enforced by API)
- [ ] Configure `COOKIE_DOMAIN` to restrict cookies to your domain
- [ ] If using AI analysis, set `ANTHROPIC_API_KEY` as an environment variable (not in code)

### Database

- Use a managed PostgreSQL service (AWS RDS, Google Cloud SQL, Supabase, etc.)
- Enable automated backups and point-in-time recovery
- Configure connection pooling (`POOL_SIZE`, `MAX_OVERFLOW`, `POOL_PRE_PING` in environment variables)
- Migrations run automatically via `entrypoint.sh` on container startup
- Index frequently queried columns (already indexed: `patient.full_name`, `patient.user_id`, `user.email`)
- Soft-deleted patients are filtered from queries via `is_deleted` flag

### Scaling

- **API:** Stateless -- scale horizontally behind a load balancer
- **WebSocket:** Each API instance manages its own connections; consider a Redis pub/sub adapter for multi-instance broadcasts
- **Celery workers:** Scale independently based on reminder queue depth
- **Database:** Use connection pooling (PgBouncer) for high-connection workloads
- **Redis:** Use Redis Sentinel or a managed service for high availability

### Monitoring

- Monitor API response times and error rates (5xx)
- Use `X-Correlation-ID` headers to trace requests across services
- Set up alerts for triage Level 1 and Level 2 assessments
- Track medication reminder delivery rates and failures
- Monitor Celery task queue depth and worker health
- Monitor WebSocket connection counts
- Use structured logging (JSON format) for log aggregation
- Monitor Docker health check status

### HIPAA Compliance Notes

If deploying in a healthcare setting:
- Encrypt data at rest (database-level encryption) and in transit (TLS)
- Audit logging is built in -- all patient data access is tracked with user ID and IP
- Correlation IDs (`X-Correlation-ID`) enable full request tracing
- Role-based access control is enforced at the API layer
- Patient ownership checks prevent cross-patient data access
- Soft delete ensures patient records are never physically removed
- Ensure BAA agreements with cloud providers
- Implement automatic session timeouts (configure `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Maintain access logs for a minimum of 6 years
- Vitals assessments are stored immutably -- medical history cannot be retroactively altered
- Account lockout protects against brute-force attacks on patient accounts
- If using AI analysis, review data handling policies with Anthropic (patient data is sent to the API)

### CI/CD

GitHub Actions runs on every push and pull request to `main`:
1. **Lint** -- `ruff check app/ tests/`
2. **Format** -- `ruff format --check app/ tests/`
3. **Security scan** -- `bandit -r app/ -ll` (static analysis for common security issues)
4. **Tests** -- `pytest tests/ -v --cov=app --cov-fail-under=90`

All four steps must pass before merging. Current: 337 tests, 91%+ coverage.

Tests use an in-memory SQLite database (`sqlite:///:memory:` with `StaticPool`) for fast, isolated execution. No external services are needed to run the test suite.

### Service Worker (PWA)

The application includes a service worker (`static/sw.js`) that provides:
- **Offline support:** Cache-first strategy for app shell assets (HTML, CSS, JS)
- **Push notifications:** Handles push events and displays native notifications
- **Auto-update:** Old caches are cleaned up on service worker activation
- **Notification click:** Opens or focuses the application window

The service worker is registered by the frontend and caches critical assets for offline use.
