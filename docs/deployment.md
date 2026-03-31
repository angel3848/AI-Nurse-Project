# Deployment Guide

## Local Development (SQLite)

The fastest way to run the project. Uses SQLite — no external services needed.

```bash
git clone https://github.com/angel3848/AI-Nurse-Project.git
cd AI-Nurse-Project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- **http://localhost:8000** — Web UI
- **http://localhost:8000/docs** — Swagger API docs

> **Note:** Celery features (medication reminders) require Redis. Everything else works with SQLite.

### Creating Demo Accounts

Register via the UI or API:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@test.com","password":"demo1234","full_name":"Demo User"}'
```

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

---

## Docker Compose (Full Stack)

Starts all services: API, PostgreSQL, Redis, Celery worker, Celery beat, and Nginx with TLS.

```bash
docker-compose up --build
```

The `docker-compose.yml` in the project root includes:
- **api** — FastAPI application (non-root user)
- **db** — PostgreSQL 15 with health checks
- **redis** — Redis 7 with health checks
- **celery-worker** — Background task processor
- **celery-beat** — Periodic task scheduler
- **nginx** — Reverse proxy with TLS termination

### First Run

After containers are up, run migrations:
```bash
docker-compose exec api alembic upgrade head
```

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
| `DATABASE_URL` | `sqlite:///./ai_nurse.db` | Database connection string |
| `JWT_SECRET_KEY` | Auto-generated (dev only) | **Required in production** — fails if unset |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiry |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection for Celery |
| `SMTP_HOST` | — | SMTP server for email notifications |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | — | SMTP username |
| `SMTP_PASSWORD` | — | SMTP password |
| `NOTIFICATION_ENABLED` | `false` | Enable email sending |
| `ALLOWED_ORIGINS` | `["http://localhost:8000"]` | CORS allowed origins |
| `COOKIE_SECURE` | `false` | Set `true` in production (requires HTTPS) |
| `COOKIE_DOMAIN` | `None` | Cookie domain restriction |
| `APP_NAME` | `AI Nurse` | Application name |

---

## Production Deployment

### Security Checklist

- [ ] Set a strong, unique `JWT_SECRET_KEY` (never use the auto-generated dev key)
- [ ] Set `COOKIE_SECURE=true` (requires HTTPS)
- [ ] Restrict `ALLOWED_ORIGINS` to your frontend domain(s)
- [ ] Use environment variables for all secrets — never commit `.env` files
- [ ] Enable TLS via nginx or a cloud load balancer
- [ ] Review rate limiting configuration for your expected load

### Database

- Use a managed PostgreSQL service (AWS RDS, Google Cloud SQL, Supabase, etc.)
- Enable automated backups and point-in-time recovery
- Configure connection pooling (`pool_size`, `max_overflow` in SQLAlchemy)
- Run migrations as part of your CI/CD pipeline: `alembic upgrade head`
- Index frequently queried columns (already indexed: `patient_id`, `user_id`, `email`)

### Scaling

- **API:** Stateless — scale horizontally behind a load balancer
- **Celery workers:** Scale independently based on reminder queue depth
- **Database:** Use connection pooling (PgBouncer) for high-connection workloads
- **Redis:** Use Redis Sentinel or a managed service for high availability

### Monitoring

- Monitor API response times and error rates (5xx)
- Set up alerts for triage Level 1 and Level 2 assessments
- Track medication reminder delivery rates and failures
- Monitor Celery task queue depth and worker health
- Use structured logging (JSON format) for log aggregation

### HIPAA Compliance Notes

If deploying in a healthcare setting:
- Encrypt data at rest (database-level encryption) and in transit (TLS)
- Audit logging is built in — all patient data access is tracked with user ID and IP
- Role-based access control is enforced at the API layer
- Patient ownership checks prevent cross-patient data access
- Ensure BAA agreements with cloud providers
- Implement automatic session timeouts (configure `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Maintain access logs for a minimum of 6 years
- Vitals assessments are stored immutably — medical history cannot be retroactively altered

### CI/CD

GitHub Actions runs on every push to `main`:
1. **Lint** — `ruff check app/ tests/`
2. **Format** — `ruff format --check app/ tests/`
3. **Tests** — `pytest tests/ -v --cov=app --cov-fail-under=90`

All three must pass before merging. Current: 249 tests, 98% coverage.
