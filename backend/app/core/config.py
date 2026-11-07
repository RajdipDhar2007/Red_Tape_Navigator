from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    secret_key: str = "dev-only-secret-key-change-me-0123456789"  # noqa: S105 - rejected in prod
    field_encryption_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/rtn.db"
    redis_url: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = ""
    oidc_issuer: str = ""
    oidc_audience: str = ""
    cors_origins: str = "http://localhost:3000"
    data_region: str = "in-mumbai"
    retention_days: int = 90
    demo_mode: bool = True
    sources_config: str = "config/sources.yaml"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    confidence_threshold: float = 0.6
    rate_limit_per_minute: int = 120
    sentry_dsn: str = ""
    integrations_mode: str = "mock"
    otel_exporter_otlp_endpoint: str = ""
    trust_proxy: bool = False
    auth_rate_limit_per_minute: int = 20
    metrics_token: str = ""
    log_level: str = "INFO"
    grievance_contact: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.is_prod and (s.secret_key.startswith("dev-only") or not s.field_encryption_key):
        raise RuntimeError("Production requires SECRET_KEY and FIELD_ENCRYPTION_KEY")
    return s
