from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    EXPENSE_SERVICE_URL: str = "http://expense-service:8002"
    SECRET_KEY: str = "change-me-in-production-use-256-bit-key"
    ALGORITHM: str = "HS256"
    REDIS_URL: str = "redis://localhost:6379"
    RATE_LIMIT_PER_MINUTE: int = 100
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
