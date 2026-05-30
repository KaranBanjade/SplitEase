from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/splitease"
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    REDIS_URL: str = "redis://redis:6379"
    SECRET_KEY: str = "change-me-in-production-use-256-bit-key"
    ALGORITHM: str = "HS256"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
