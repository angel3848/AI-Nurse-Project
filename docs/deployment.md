# Deployment Guide

## Local Development

### Quick Start

```bash
# Clone and set up
git clone https://github.com/angel3848/AI-Nurse-Project.git
cd AI-Nurse-Project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start PostgreSQL and Redis (via Docker)
docker run -d --name ai-nurse-db -p 5432:5432 \
  -e POSTGRES_DB=ai_nurse_db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  postgres:15

docker run -d --name ai-nurse-redis -p 6379:6379 redis:7

# Run migrations and start
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Celery Workers

In a separate terminal (with venv activated):

```bash
# Start the Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery Beat (for scheduled reminders)
celery -A app.celery_app beat --loglevel=info
```

---

## Docker Deployment

### Docker Compose

Create a `docker-compose.yml`:

```yaml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  celery-worker:
    build: .
    env_file:
      - .env
    depends_on:
      - db
      - redis
    command: celery -A app.celery_app worker --loglevel=info

  celery-beat:
    build: .
    env_file:
      - .env
    depends_on:
      - redis
    command: celery -A app.celery_app beat --loglevel=info

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ai_nurse_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Run with Docker Compose

```bash
docker-compose up -d
docker-compose exec api alembic upgrade head
```

---

## Production Considerations

### Security
- Use strong, unique values for `SECRET_KEY` and `JWT_SECRET_KEY`
- Enable HTTPS via a reverse proxy (nginx or a cloud load balancer)
- Restrict `ALLOWED_ORIGINS` to your frontend domain(s)
- Use environment variables for all secrets — never commit `.env` files
- Enable rate limiting on authentication endpoints

### Database
- Use a managed PostgreSQL service (AWS RDS, Google Cloud SQL, etc.)
- Enable automated backups and point-in-time recovery
- Use connection pooling (PgBouncer) for production workloads
- Run migrations as part of your CI/CD pipeline, not at startup

### Monitoring
- Use structured logging (JSON format) for log aggregation
- Monitor API response times and error rates
- Set up alerts for triage Level 1 and Level 2 assessments
- Track medication reminder delivery rates and failures

### Scaling
- The FastAPI application is stateless — scale horizontally behind a load balancer
- Scale Celery workers independently based on reminder queue depth
- Use Redis Sentinel or a managed Redis service for high availability

### HIPAA Compliance Notes
If deploying in a healthcare setting in the United States:
- Encrypt data at rest and in transit
- Implement audit logging for all patient data access
- Use role-based access control (built into the application)
- Ensure BAA agreements with cloud providers
- Implement automatic session timeouts
- Maintain access logs for a minimum of 6 years
