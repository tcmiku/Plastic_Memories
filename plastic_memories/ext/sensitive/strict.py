import re

from ..interfaces import SensitivePolicy


class StrictDenyPolicy:
    _patterns = [
        re.compile(r"\bpassword\b", re.I),
        re.compile(r"\bssn\b", re.I),
        re.compile(r"\bcredit\s*card\b", re.I),
        re.compile(r"\bsecret\b", re.I),
        re.compile(r"\bapi[_-]?key\b", re.I),
        re.compile(r"\btoken\b", re.I),
        re.compile(r"\b[0-9]{16}\b"),
    ]

    def check(self, text: str) -> tuple[bool, str | None]:
        for pat in self._patterns:
            if pat.search(text):
                return True, f"sensitive:{pat.pattern}"
        return False, None
