from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict

from fastapi import Header, HTTPException

from .context import get_persona_id, get_request_id, set_request_context
from .http import fail


@dataclass(frozen=True)
class AuthedUser:
    user_id: str


def parse_api_keys(env_str: str | None) -> Dict[str, str]:
    if not env_str:
        return {}
    items: Dict[str, str] = {}
    for part in env_str.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            continue
        key, user_id = part.split(":", 1)
        key = key.strip()
        user_id = user_id.strip()
        if not key or not user_id:
            continue
        items[key] = user_id
    return items


def require_user(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> AuthedUser:
    mapping = parse_api_keys(os.getenv("PLASTIC_MEMORIES_API_KEYS"))
    if not x_api_key or x_api_key not in mapping:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_id = mapping[x_api_key]
    set_request_context(get_request_id(), user_id=user_id, persona_id=get_persona_id())
    return AuthedUser(user_id=user_id)
