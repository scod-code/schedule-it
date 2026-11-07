from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    stripe_secret_key: str = "sk_test_placeholder"
    stripe_publishable_key: str = "pk_test_placeholder"
    stripe_webhook_secret: str = "whsec_placeholder"
    stripe_price_id: str = "price_placeholder"
    base_url: str = "http://localhost:8000"
    app_env: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
