from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List
import secrets


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    # App
    APP_NAME: str = "EnterpriseAnalytics"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://analytics:analytics_pass@localhost:5432/analyticsdb"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://yourdomain.com"]

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx", ".json"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # Background tasks
    MAX_WORKERS: int = 4


settings = Settings()
