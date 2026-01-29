from .config import get_settings
from .utils import ensure_dir


def ensure_db_dir() -> None:
    settings = get_settings()
    ensure_dir(settings.db_path.parent)
