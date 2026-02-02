import os
import sys
from pathlib import Path

def _is_test_runtime() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if os.getenv("COVERAGE_FILE") or os.getenv("COVERAGE_PROCESS_START"):
        return True
    return any("pytest" in arg for arg in sys.argv)


if _is_test_runtime():
    ROOT = Path(__file__).resolve().parent
    TMP_ROOT = ROOT / ".test_tmp"
    TMP_ROOT.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("COVERAGE_FILE", str(TMP_ROOT / ".coverage"))
    os.environ.setdefault("TMPDIR", str(TMP_ROOT))
    os.environ.setdefault("TMP", str(TMP_ROOT))
    os.environ.setdefault("TEMP", str(TMP_ROOT))
