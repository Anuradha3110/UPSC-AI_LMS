"""
Central settings object — every other module reads config through this,
never through os.environ directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str
    mongodb_db: str = "nirdesh"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    anthropic_api_key: str | None = None
    # Sonnet/Haiku-class routing per §08 of the architecture is a real cost
    # lever once grading volume is high — swap this without touching
    # services/grading.py. Defaults to Opus for grading quality.
    grading_model: str = "claude-opus-5"

    cors_origins: str = "http://localhost:3000"

    # MOD-03 daily current-affairs refresh (see services/news_ingest.py).
    news_ingest_enabled: bool = True
    news_max_items_per_run: int = 20

    # MOD-12 Razorpay Payment Gateway integration
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
