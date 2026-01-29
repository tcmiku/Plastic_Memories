import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .config import get_settings
from .context import get_request_id, get_user_id, get_persona_id
from .utils import ensure_dir, now_ts


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": now_ts(),
            "level": record.levelname.lower(),
            "event": getattr(record, "event", "log"),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
            "user_id": getattr(record, "user_id", None) or get_user_id(),
            "persona_id": getattr(record, "persona_id", None) or get_persona_id(),
            "duration_ms": getattr(record, "duration_ms", None),
        }
        if record.exc_info:
            payload["err"] = self.formatException(record.exc_info)
        msg = record.getMessage()
        if msg and msg != payload.get("event"):
            payload["msg"] = msg
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


_logger = None


def configure_logging() -> logging.Logger:
    global _logger
    if _logger:
        return _logger
    settings = get_settings()
    log_dir: Path = settings.log_dir
    ensure_dir(log_dir)
    logger = logging.getLogger("plastic_memories")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_dir / "plastic_memories.log", maxBytes=2_000_000, backupCount=5)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    _logger = logger
    return logger


def log_event(event: str, **fields) -> None:
    logger = configure_logging()
    extra = {"event": event}
    extra.update(fields)
    logger.info(event, extra=extra)
