from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    port: int = 8000
    environment: str = "development"
    database_url: str
    redis_url: str = "redis://localhost:6379"
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()