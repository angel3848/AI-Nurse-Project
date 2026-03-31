import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Nurse"
    app_version: str = "0.1.0"
    debug: bool = False
    app_env: str = "development"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    database_url: str = "sqlite:///./ai_nurse.db"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    redis_url: str = "redis://localhost:6379/0"
    cookie_secure: bool = False  # Set True in production (requires HTTPS)
    cookie_domain: str | None = None

    # Connection pool settings (ignored for SQLite)
    pool_size: int = 5
    max_overflow: int = 10
    pool_pre_ping: bool = True

    # AI analysis (Claude API)
    anthropic_api_key: str = ""
    ai_analysis_enabled: bool = False

    # Email notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@ainurse.local"
    smtp_from_name: str = "AI Nurse"
    notification_enabled: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Fail-fast: refuse to start without a JWT secret in production
if settings.app_env == "production" and not settings.jwt_secret_key:
    raise RuntimeError(
        "JWT_SECRET_KEY must be set in production. "
        'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )

# In development, auto-generate a random secret if none provided
if not settings.jwt_secret_key:
    settings.jwt_secret_key = secrets.token_urlsafe(32)
