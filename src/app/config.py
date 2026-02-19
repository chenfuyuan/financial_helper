from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "myapp"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/myapp"

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "DEBUG"


settings = Settings()
