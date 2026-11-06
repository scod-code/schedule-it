"""
Application configuration loaded from environment variables.
Copy .env.example to .env and fill in real values before running.
"""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""          # price id for the £9 product

    # App
    app_base_url: str = "http://localhost:8000"
    secret_key: str = "change-me-in-production"
    solver_time_limit_seconds: int = 10

    # Storage
    jobs_dir: str = os.path.join(os.path.dirname(__file__), "..", "jobs")
    data_retention_days: int = 30

    # Environment
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
