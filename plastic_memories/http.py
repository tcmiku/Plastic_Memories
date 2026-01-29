from __future__ import annotations

from typing import Any

from .context import get_request_id


def ok(data: Any) -> dict:
    return {"ok": True, "data": data}


def fail(code: str, message: str, details: Any = None, request_id: str | None = None) -> dict:
    return {
        "ok": False,
        "error": {"code": code, "message": message, "details": details},
        "request_id": request_id or get_request_id(),
    }
