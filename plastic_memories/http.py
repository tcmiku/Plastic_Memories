from __future__ import annotations

from typing import Any

from .context import get_request_id
from .utils import gen_request_id


def ok(data: Any) -> dict:
    request_id = get_request_id() or gen_request_id()
    return {"ok": True, "request_id": request_id, "data": data}


def fail(code: str, message: str, detail: Any = None, request_id: str | None = None) -> dict:
    rid = request_id or get_request_id() or gen_request_id()
    return {
        "ok": False,
        "error": {"code": code, "message": message, "detail": detail},
        "request_id": rid,
    }
