"""Structured JSON logging. Every event is passed through PII redaction (Aadhaar / PAN patterns)."""
import logging
import sys

import structlog

from app.core.crypto import redact


def _redact_processor(_, __, event_dict):
    return redact(event_dict)


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str = "rtn"):
    return structlog.get_logger(name)
