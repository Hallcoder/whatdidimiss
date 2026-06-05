from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "whatdidimiss"
    app_env: str = "development"
    debug: bool = False
    auth_disabled: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    fernet_key: str = "change-me-generate-with-fernet"

    # Database
    database_url: str = "postgresql+asyncpg://whatdidimiss:localpass@localhost:5432/whatdidimiss"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Google Cloud
    gcp_project_id: str = ""
    gcs_bucket_name: str = ""
    google_application_credentials: str | None = None

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 8192
    openai_temperature: float = 0.3

    # YouTube
    youtube_api_daily_quota: int = 10000
    google_api_key: str = ""
    ytdlp_cookies_file: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Frontend
    frontend_url: str = "http://localhost:3000"


settings = Settings()
