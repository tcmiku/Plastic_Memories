from ..interfaces import SensitivePolicy
from ...logging import log_event


class RuleBasedJudge:
    def __init__(self, sensitive: SensitivePolicy) -> None:
        self._sensitive = sensitive

    def judge(self, payload: dict) -> dict:
        text = payload.get("content") or ""
        hit, reason = self._sensitive.check(text)
        if hit:
            log_event("sensitive.hit", user_id=payload.get("user_id"), persona_id=payload.get("persona_id"))
            return {"allow": False, "reason": reason or "sensitive"}
        log_event("judge.run", user_id=payload.get("user_id"), persona_id=payload.get("persona_id"))
        return {"allow": True, "reason": None}
