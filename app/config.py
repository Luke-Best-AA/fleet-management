from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://localhost/fleet_management"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    SESSION_LIFETIME_SECONDS: int = 3600
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_SECONDS: int = 900
    APP_NAME: str = "Fleet Management"
    SECURE_COOKIES: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
