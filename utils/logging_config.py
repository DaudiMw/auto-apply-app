import hashlib
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}
_HANDLER_MARKER = "_auto_apply_handler"
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON, including any `extra` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def hash_id(value: Optional[str]) -> str:
    """Returns a short, non-reversible identifier so user IDs/emails never appear in logs."""
    if not value:
        return "anonymous"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def setup_logging() -> None:
    """Configures root logging once (safe to call on every Streamlit rerun).

    Env vars: LOG_LEVEL (default INFO), LOG_DIR (default ./logs, file logging skipped if unwritable).
    """
    root = logging.getLogger()
    if any(getattr(h, _HANDLER_MARKER, False) for h in root.handlers):
        return

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name if level_name in _VALID_LEVELS else "INFO")
    root.setLevel(level)

    formatter = JsonFormatter()
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    log_dir = os.environ.get("LOG_DIR", "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                os.path.join(log_dir, "app.log"), maxBytes=5_000_000, backupCount=5, encoding="utf-8"
            )
        )
    except OSError:
        pass  # Read-only filesystem etc.: fall back to console logging only.

    for handler in handlers:
        handler.setFormatter(formatter)
        setattr(handler, _HANDLER_MARKER, True)
        root.addHandler(handler)

    # Keep third-party libraries quiet unless explicitly debugging.
    for noisy in ("boto3", "botocore", "urllib3", "watchdog"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
