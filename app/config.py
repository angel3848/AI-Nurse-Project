from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Nurse"
    app_version: str = "0.1.0"
    debug: bool = False
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    database_url: str = "sqlite:///./ai_nurse.db"
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
