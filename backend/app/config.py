from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    stripe_secret_key: str = "sk_test_placeholder"
    stripe_publishable_key: str = "pk_test_placeholder"
    stripe_webhook_secret: str = "whsec_placeholder"
    stripe_price_id: str = "price_placeholder"
    app_base_url: str = "http://localhost:8000"
    secret_key: str = "development-only-change-me"
    solver_time_limit_seconds: int = Field(default=10, ge=1)
    jobs_dir: str = "./jobs"
    data_retention_days: int = Field(default=30, ge=1)
    debug: bool = False
    app_env: str = "development"


settings = Settings()
