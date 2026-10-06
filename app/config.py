from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` if present)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "devops-service-template"
    environment: str = "production"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 10

    # Max number of items returned by list endpoints.
    max_page_size: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
