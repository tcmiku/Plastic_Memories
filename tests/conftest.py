import shutil
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    root = Path.cwd() / ".test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    db_dir = root / uuid.uuid4().hex
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "test.db"
    monkeypatch.setenv("PLASTIC_MEMORIES_DB_PATH", str(db_path))
    monkeypatch.setenv("PLASTIC_MEMORIES_BACKEND", "sqlite")
    monkeypatch.setenv("PLASTIC_MEMORIES_LOG_DIR", str(root / "logs"))
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
    shutil.rmtree(db_dir, ignore_errors=True)


@pytest.fixture
def anyio_backend():
    return "asyncio"
