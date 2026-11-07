"""Error-tracking hook. Uses Sentry when SENTRY_DSN is set and sentry-sdk is installed; always logs."""
from app.core.config import get_settings
from app.core.logging import get_logger

_log = get_logger("errors")
_sentry_ready = False


def init_error_tracking() -> None:
    global _sentry_ready
    dsn = get_settings().sentry_dsn
    if not dsn:
        return
    try:  # pragma: no cover - optional dependency
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, send_default_pii=False, traces_sample_rate=0.0)
        _sentry_ready = True
    except ImportError:  # pragma: no cover
        _log.warning("sentry_dsn_set_but_sdk_missing")


def capture_exception(exc: BaseException, **context: str) -> None:
    _log.error("unhandled_exception", error_type=type(exc).__name__, **context)
    if _sentry_ready:  # pragma: no cover
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
