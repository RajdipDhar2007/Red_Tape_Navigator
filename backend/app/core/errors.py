"""Error-tracking hook. Uses Sentry when SENTRY_DSN is set and sentry-sdk is installed; always logs."""
from app.core.config import get_settings
from app.core.crypto import redact
from app.core.logging import get_logger

_log = get_logger("errors")
_sentry_ready = False


def init_error_tracking() -> None:
    global _sentry_ready
    s = get_settings()
    dsn = s.sentry_dsn.strip()
    if not dsn:
        _sentry_ready = False
        return
    try:  # pragma: no cover - optional dependency
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, environment=s.app_env, send_default_pii=False, traces_sample_rate=0.0)
        _sentry_ready = True
    except ImportError:  # pragma: no cover
        _sentry_ready = False
        _log.warning("sentry_dsn_set_but_sdk_missing")


def capture_exception(exc: BaseException, **context: str) -> None:
    safe_ctx = redact(context)
    _log.error("unhandled_exception", error_type=type(exc).__name__, **safe_ctx)
    if _sentry_ready:  # pragma: no cover
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
