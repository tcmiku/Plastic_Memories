import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .config import get_settings
from .context import get_request_id, get_user_id, get_persona_id
from .utils import ensure_dir, now_ts


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        settings = get_settings()
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "event": getattr(record, "event", "log"),
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
            "user_id": getattr(record, "user_id", None) or get_user_id(),
            "persona_id": getattr(record, "persona_id", None) or get_persona_id(),
            "duration_ms": getattr(record, "duration_ms", None),
            "backend": settings.backend,
            "recall": settings.recall,
            "judge": settings.judge,
            "profile": settings.profile,
            "sensitive": settings.sensitive,
            "events": settings.events,
        }
        if record.exc_info:
            payload["err"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


_logger = None


def configure_logging() -> logging.Logger:
    global _logger
    if _logger:
        return _logger
    settings = get_settings()
    logger = logging.getLogger("plastic_memories")
    log_level = os.getenv("PLASTIC_MEMORIES_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    formatter = JsonFormatter()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    log_path = os.getenv("LOG_PATH")
    log_dir = os.getenv("PLASTIC_MEMORIES_LOG_DIR")
    if log_path or log_dir:
        if log_path:
            file_path = Path(log_path)
        else:
            file_path = Path(log_dir) / "plastic_memories.log"
        ensure_dir(file_path.parent)
        file_handler = RotatingFileHandler(file_path, maxBytes=2_000_000, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.propagate = False
    _logger = logger
    return logger


def log_event(event: str, **fields) -> None:
    logger = configure_logging()
    extra = {"event": event}
    extra.update(fields)
    logger.info(event, extra=extra)
