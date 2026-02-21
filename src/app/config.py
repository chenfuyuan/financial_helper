from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_NAME: str = "financial_helper"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/financial_helper"
    TUSHARE_TOKEN: str = ""

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "DEBUG"

    # 数据工程配置
    CONCEPT_SYNC_BATCH_SIZE: int = 50  # 概念同步批次大小
    CONCEPT_SYNC_TIMEOUT_SECONDS: int = 300  # 概念同步超时时间（秒）
    CONCEPT_SYNC_MEMORY_THRESHOLD_MB: int = 1024  # 内存使用阈值（MB）


settings = Settings()
