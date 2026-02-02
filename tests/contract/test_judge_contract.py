from plastic_memories.ext.judge.rules import RuleBasedJudge
from plastic_memories.ext.sensitive.strict import StrictDenyPolicy


class JudgeContract:
    def test_sensitive_denied(self):
        judge = RuleBasedJudge(StrictDenyPolicy())
        result = judge.judge({"content": "my password is 123"})
        assert result["decision"] == "deny"


class TestJudgeContract(JudgeContract):
    pass
