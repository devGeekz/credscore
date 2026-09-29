from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    port: int = 8000
    environment: str = "development"
    database_url: str
    redis_url: str = "redis://localhost:6379"
    # set to memory:// in dev when redis isn't running; empty = use redis_url
    rate_limit_storage_uri: str = ""
    jwt_secret: str
    jwt_expires_in: str = "7d"
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    storage_bucket: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_endpoint: str = ""
    app_url: str = "http://localhost:8000"
    webhook_signing_secret: str = "dev-secret"

    # absolute so it loads regardless of the caller's cwd (tests, workers)
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()

