import json
import time
import uuid
from pathlib import Path


def now_ts() -> int:
    return int(time.time())


def gen_request_id() -> str:
    return uuid.uuid4().hex


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def dumps_json(value) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
