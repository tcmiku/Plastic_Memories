import json
import re
from pathlib import Path

from plastic_memories.api import app
from plastic_memories import schemas


def _schema_fields(model) -> set[str]:
    return set(model.model_fields.keys())


def test_requests_http_static_contract():
    http_path = Path(__file__).resolve().parents[1] / "docs" / "requests.http"
    content = http_path.read_text(encoding="utf-8")

    vars_found = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", content)
    allowed_vars = {"baseUrl", "apiKey", "personaId"}
    assert all(var in allowed_vars for var in vars_found)

    openapi_paths = set(app.openapi().get("paths", {}).keys())

    path_to_fields = {
        "/memory/write": _schema_fields(schemas.MemoryWriteRequest),
        "/memory/confirm": _schema_fields(schemas.MemoryConfirmRequest),
        "/memory/revoke": _schema_fields(schemas.MemoryRevokeRequest),
        "/memory/forget": _schema_fields(schemas.MemoryForgetRequest),
        "/persona/slots/get": _schema_fields(schemas.PersonaSlotsGetRequest),
        "/goals/create": _schema_fields(schemas.GoalCreateRequest),
        "/goals/update_status": _schema_fields(schemas.GoalUpdateStatusRequest),
        "/goals/link": _schema_fields(schemas.GoalLinkRequest),
    }

    blocks = [b.strip() for b in content.split("###") if b.strip()]
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        request_line = next((line for line in lines if line.startswith("POST ") or line.startswith("GET ")), None)
        if not request_line:
            continue
        method, url = request_line.split(" ", 1)
        path = url.replace("{{baseUrl}}", "").split("?")[0]
        assert path in openapi_paths

        if method == "GET":
            continue

        json_start = block.find("{")
        if json_start == -1:
            continue
        body_text = block[json_start:]
        try:
            body = json.loads(body_text)
        except Exception:
            continue

        if path not in path_to_fields:
            continue
        assert set(body.keys()).issubset(path_to_fields[path])
