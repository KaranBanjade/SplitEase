from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/splitease"
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    EXPENSE_SERVICE_URL: str = "http://expense-service:8002"
    REDIS_URL: str = "redis://redis:6379"

    # SMTP / email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@splitease.app"
    APP_URL: str = "http://localhost:3000"

    # Web Push (VAPID)
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = "admin@splitease.app"

    class Config:
        env_file = ".env"


settings = Settings()
