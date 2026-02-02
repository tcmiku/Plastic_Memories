from ..interfaces import SensitivePolicy
from ...logging import log_event


class RuleBasedJudge:
    def __init__(self, sensitive: SensitivePolicy) -> None:
        self._sensitive = sensitive

    def judge(self, payload: dict) -> dict:
        text = payload.get("content") or ""
        if len(text) > 2000:
            return {"decision": "deny", "reason": "content_too_long"}
        hit, reason = self._sensitive.check(text)
        if hit:
            log_event("sensitive.hit", user_id=payload.get("user_id"), persona_id=payload.get("persona_id"))
            return {"decision": "deny", "reason": reason or "sensitive"}
        if payload.get("source_type") == "model_inferred":
            return {"decision": "allow_candidate", "reason": None}
        log_event("judge.run", user_id=payload.get("user_id"), persona_id=payload.get("persona_id"))
        return {"decision": "allow_active", "reason": None}
