import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("COVERAGE_FILE", str(ROOT / ".test_tmp" / ".coverage"))


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("PLASTIC_MEMORIES_DB_PATH", str(db_path))
    monkeypatch.setenv("PLASTIC_MEMORIES_BACKEND", "sqlite")
    monkeypatch.setenv("PLASTIC_MEMORIES_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("PLASTIC_MEMORIES_API_KEYS", "testkey-a:userA,testkey-b:userB")
    import plastic_memories.config as config
    config._settings = None
    import plastic_memories.ext.registry as registry
    registry._storage = None
    registry._recall = None
    registry._judge = None
    registry._profile = None
    registry._sensitive = None
    registry._events = None
    yield


@pytest.fixture
def client():
    from plastic_memories.api import app

    return TestClient(app)


def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


@pytest.fixture
def anyio_backend():
    return "asyncio"
