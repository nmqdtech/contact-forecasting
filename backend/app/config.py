from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql+asyncpg://forecasting:forecasting@localhost:5432/forecasting"
    )
    SYNC_DATABASE_URL: str = (
        "postgresql+psycopg2://forecasting:forecasting@localhost:5432/forecasting"
    )
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    UPLOAD_MAX_MB: int = 50

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
