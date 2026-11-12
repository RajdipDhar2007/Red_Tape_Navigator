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
    # Single-instance hosting without a separate worker/Redis: run the scheduled jobs inside the API process.
    run_scheduler: bool = False
    # First officer account, created/promoted at start when both are set (for hosts without a shell). Remove after first sign-in.
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    storage_backend: str = "local"  # local | s3
    storage_local_dir: str = "./data/vault"
    storage_bucket: str = ""
    storage_region: str = "ap-south-1"
    storage_endpoint_url: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    max_upload_bytes: int = 5_242_880  # 5 MB
    document_scan_mode: str = "disabled"  # disabled | external
    document_scan_url: str = ""

    @field_validator("database_url", mode="after")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        """Managed hosts (Render, Heroku-style) hand out postgres:// or postgresql:// URLs; SQLAlchemy needs asyncpg."""
        for plain in ("postgres://", "postgresql://"):
            if v.startswith(plain):
                v = "postgresql+asyncpg://" + v[len(plain):]
                break
        if v.startswith("postgresql+asyncpg://") and "?" in v:
            # libpq-style options (Neon, Supabase, Render external URLs) are not understood by asyncpg
            base, _, query = v.partition("?")
            kept = []
            for part in query.split("&"):
                key, _, val = part.partition("=")
                if key == "sslmode":
                    if val != "disable":
                        kept.append("ssl=require")
                elif key not in ("channel_binding", "options"):
                    kept.append(part)
            v = base + ("?" + "&".join(kept) if kept else "")
        return v

    @field_validator("field_encryption_key", mode="after")
    @classmethod
    def _urlsafe_key(cls, v: str) -> str:
        """Hosts that generate secrets (Render generateValue) emit standard base64; Fernet wants the url-safe alphabet."""
        return v.replace("+", "-").replace("/", "_")

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
    if bool(s.anthropic_api_key.strip()) != bool(s.anthropic_model.strip()):
        problems.append("ANTHROPIC_API_KEY and ANTHROPIC_MODEL must both be set when enabling the Anthropic LLM provider")
    if bool(s.msg91_authkey.strip()) != bool(s.msg91_template_id.strip()):
        problems.append("MSG91_AUTHKEY and MSG91_TEMPLATE_ID must both be set when enabling MSG91 SMS")
    if bool(s.digio_client_id.strip()) != bool(s.digio_client_secret.strip()):
        problems.append("DIGIO_CLIENT_ID and DIGIO_CLIENT_SECRET must both be set when enabling Digio")
    if s.digio_configured and not s.digio_webhook_secret:
        problems.append("DIGIO_WEBHOOK_SECRET is required when Digio credentials are set (webhook checksum)")
    if s.digio_configured and s.digio_env not in ("sandbox", "production"):
        problems.append("DIGIO_ENV must be sandbox or production")
    if s.digio_configured and s.digio_env == "production" and s.digio_webhook_ips and not s.trust_proxy:
        problems.append("TRUST_PROXY must be true for DIGIO_WEBHOOK_IPS to be enforced behind Render's proxy")
    if bool(s.bootstrap_admin_email) != bool(s.bootstrap_admin_password):
        problems.append("BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD must be set together (or both left empty)")
    elif s.bootstrap_admin_password and len(s.bootstrap_admin_password) < 12:
        problems.append("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")
    if s.storage_backend not in ("local", "s3"):
        problems.append("STORAGE_BACKEND must be local or s3")
    if s.storage_backend == "s3" and not (
        s.storage_bucket and s.storage_region and s.storage_access_key_id and s.storage_secret_access_key
    ):
        problems.append(
            "STORAGE_BUCKET, STORAGE_REGION, STORAGE_ACCESS_KEY_ID and STORAGE_SECRET_ACCESS_KEY are required when STORAGE_BACKEND=s3"
        )
    if s.document_scan_mode not in ("disabled", "external"):
        problems.append("DOCUMENT_SCAN_MODE must be disabled or external")
    if s.document_scan_mode == "external" and not s.document_scan_url.startswith(("https://", "http://")):
        problems.append("DOCUMENT_SCAN_URL is required when DOCUMENT_SCAN_MODE=external")
    if s.demo_mode:
        problems.append("DEMO_MODE must be false (it exposes demo accounts and simulated integrations)")
    return problems
