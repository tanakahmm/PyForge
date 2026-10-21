import logging
import logging.config
import os

from pyforge.observability.context import request_id_var


class RequestIdFilter(logging.Filter):
    """Add a request ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging() -> None:
    """Configure consistent application-wide logging."""
    level = os.getenv("PYFORGE_LOG_LEVEL", "INFO").upper()

    if not hasattr(logging, level) or not isinstance(
        getattr(logging, level), int
    ):
        level = "INFO"

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": RequestIdFilter,
            },
        },
        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s %(levelname)s "
                    "%(name)s request_id=%(request_id)s "
                    "%(message)s"
                ),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "standard",
                "filters": ["request_id"],
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
    })