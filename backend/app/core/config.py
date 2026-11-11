from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    secret_key: str = "dev-only-secret-key-change-me-0123456789"  # noqa: S105 - rejected in prod
    field_encryption_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/rtn.db"
    redis_url: str = ""
    llm_provider: str = "auto"  # auto | ollama | gemini | anthropic | none
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""
    gemini_api_key: str = ""
    gemini_model: str = ""
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
    web_base_url: str = "http://localhost:3000"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    msg91_authkey: str = ""
    msg91_template_id: str = ""
    msg91_text_var: str = "var1"
    digio_client_id: str = ""
    digio_client_secret: str = ""
    digio_env: str = "sandbox"  # sandbox | production
    digio_webhook_secret: str = ""
    digio_webhook_ips: str = ""  # comma list; enforced only when TRUST_PROXY=true (see api/webhooks.py)
    digio_digilocker_template: str = "DIGILOCKER_AADHAAR_PAN"
    reset_token_minutes: int = 30
    lockout_threshold: int = 5
    lockout_minutes: int = 15

    @field_validator("database_url", mode="after")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        """Managed hosts (Render, Heroku-style) hand out postgres:// or postgresql:// URLs; SQLAlchemy needs asyncpg."""
        for plain in ("postgres://", "postgresql://"):
            if v.startswith(plain):
                return "postgresql+asyncpg://" + v[len(plain):]
        return v

    @property
    def digio_configured(self) -> bool:
        return bool(self.digio_client_id and self.digio_client_secret)

    @property
    def digio_ip_list(self) -> list[str]:
        return [i.strip() for i in self.digio_webhook_ips.split(",") if i.strip()]

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.field_encryption_key:  # fail fast with a clear message instead of at the first Aadhaar/PAN answer
        from cryptography.fernet import Fernet

        for k in (x.strip() for x in s.field_encryption_key.split(",") if x.strip()):
            try:
                Fernet(k.encode())
            except ValueError as exc:
                raise RuntimeError(
                    "FIELD_ENCRYPTION_KEY is not a valid Fernet key (32 url-safe base64 bytes). Generate one with `make keygen`. "
                    "Keep comments on their own line in .env files."
                ) from exc
    if s.is_prod:
        problems = production_problems(s)
        if problems:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
    return s


def production_problems(s: Settings) -> list[str]:
    """Everything that must not be true when APP_ENV=prod. Reported together so one deploy fixes all of it."""
    problems: list[str] = []
    if s.secret_key.startswith(("dev-only", "change-me")) or len(s.secret_key) < 32:
        problems.append("SECRET_KEY must be a real secret of at least 32 characters")
    if not s.field_encryption_key:
        problems.append("FIELD_ENCRYPTION_KEY is required (make keygen)")
    if s.database_url.startswith("sqlite"):
        problems.append("DATABASE_URL must be PostgreSQL, not SQLite")
    if not s.cors_list or any("localhost" in o or "127.0.0.1" in o for o in s.cors_list):
        problems.append("CORS_ORIGINS must list the real https origin(s), not localhost")
    elif any(not o.startswith("https://") for o in s.cors_list):
        problems.append("CORS_ORIGINS must use https://")
    if not s.web_base_url.startswith("https://"):
        problems.append("WEB_BASE_URL must be the public https URL (used in password-reset emails)")
    if not (s.smtp_host and s.smtp_from):
        problems.append("SMTP_HOST and SMTP_FROM are required (password-reset and reminder email)")
    if not s.grievance_contact:
        problems.append("GRIEVANCE_CONTACT is required (DPDP grievance officer shown to citizens)")
    if s.digio_configured and not s.digio_webhook_secret:
        problems.append("DIGIO_WEBHOOK_SECRET is required when Digio credentials are set (webhook checksum)")
    if s.digio_configured and s.digio_env not in ("sandbox", "production"):
        problems.append("DIGIO_ENV must be sandbox or production")
    if s.digio_configured and s.digio_env == "production" and s.digio_webhook_ips and not s.trust_proxy:
        problems.append("TRUST_PROXY must be true for DIGIO_WEBHOOK_IPS to be enforced behind Render's proxy")
    if s.demo_mode:
        problems.append("DEMO_MODE must be false (it exposes demo accounts and simulated integrations)")
    return problems
