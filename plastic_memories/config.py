import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_db_path() -> Path:
    env = os.getenv("PLASTIC_MEMORIES_DB_PATH")
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "PlasticMemories" / "plastic_memories.db"
    return Path.home() / ".plastic_memories" / "plastic_memories.db"


def _default_log_dir() -> Path:
    env = os.getenv("PLASTIC_MEMORIES_LOG_DIR")
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "PlasticMemories" / "logs"
    return Path.home() / ".plastic_memories" / "logs"


def _default_template_root() -> Path:
    env = os.getenv("PLASTIC_MEMORIES_TEMPLATE_ROOT")
    if env:
        return Path(env).expanduser()
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "personas"


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(default_factory=_default_db_path)
    log_dir: Path = field(default_factory=_default_log_dir)
    template_root: Path = field(default_factory=_default_template_root)
    backend: str = field(default_factory=lambda: os.getenv("PLASTIC_MEMORIES_BACKEND", "sqlite"))
    recall: str = field(default_factory=lambda: os.getenv("PLASTIC_MEMORIES_RECALL", "keyword"))
    judge: str = field(default_factory=lambda: os.getenv("PLASTIC_MEMORIES_JUDGE", "rules"))
    profile: str = field(default_factory=lambda: os.getenv("PLASTIC_MEMORIES_PROFILE", "markdown"))
    sensitive: str = field(default_factory=lambda: os.getenv("PLASTIC_MEMORIES_SENSITIVE", "strict"))
    events: str = field(default_factory=lambda: os.getenv("PLASTIC_MEMORIES_EVENTS", "none"))
    message_snippet_days: int = field(default_factory=lambda: int(os.getenv("PLASTIC_MEMORIES_SNIPPET_DAYS", "7")))
    max_snippets: int = field(default_factory=lambda: int(os.getenv("PLASTIC_MEMORIES_SNIPPET_LIMIT", "20")))
    busy_timeout_ms: int = field(default_factory=lambda: int(os.getenv("PLASTIC_MEMORIES_BUSY_TIMEOUT_MS", "5000")))
    profile_max_chars: int = field(default_factory=lambda: int(os.getenv("PLASTIC_MEMORIES_PROFILE_MAX_CHARS", "2000")))


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
