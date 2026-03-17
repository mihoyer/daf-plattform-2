"""Zentrale Konfiguration der DaF-Plattform v2."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""

    # Datenbank (SQLite für einfaches Deployment neben v1)
    database_url: str = "sqlite+aiosqlite:///./daf_plattform_v2.db"

    # Sicherheit
    secret_key: str = "change-me-in-production"
    admin_password: str = "admin"
    admin_username: str = "admin"

    # App
    base_url: str = "http://localhost:8002"
    debug: bool = False
    max_audio_mb: int = 25
    delete_audio_after_analysis: bool = True
    session_expiry_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
