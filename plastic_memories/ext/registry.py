from .interfaces import StorageBackend, RecallEngine, JudgeEngine, ProfileBuilder, SensitivePolicy, EventSink
from .backends.sqlite import SQLiteStorage
from .recall.keyword import KeywordRecallEngine
from .judge.rules import RuleBasedJudge
from .profile.markdown import MarkdownProfileBuilder
from .sensitive.strict import StrictDenyPolicy
from .events.noop import NoopEventSink
from .events.ws import WebSocketEventSink
from ..config import get_settings

_storage: StorageBackend | None = None
_recall: RecallEngine | None = None
_judge: JudgeEngine | None = None
_profile: ProfileBuilder | None = None
_sensitive: SensitivePolicy | None = None
_events: EventSink | None = None


def get_storage() -> StorageBackend:
    global _storage
    if _storage:
        return _storage
    settings = get_settings()
    if settings.backend == "sqlite":
        _storage = SQLiteStorage()
    else:
        raise ValueError(f"Unknown backend: {settings.backend}")
    _storage.init()
    return _storage


def get_profile_builder() -> ProfileBuilder:
    global _profile
    if _profile:
        return _profile
    settings = get_settings()
    if settings.profile == "markdown":
        _profile = MarkdownProfileBuilder()
    else:
        raise ValueError(f"Unknown profile: {settings.profile}")
    return _profile


def get_sensitive_policy() -> SensitivePolicy:
    global _sensitive
    if _sensitive:
        return _sensitive
    settings = get_settings()
    if settings.sensitive == "strict":
        _sensitive = StrictDenyPolicy()
    else:
        raise ValueError(f"Unknown sensitive policy: {settings.sensitive}")
    return _sensitive


def get_judge() -> JudgeEngine:
    global _judge
    if _judge:
        return _judge
    settings = get_settings()
    if settings.judge == "rules":
        _judge = RuleBasedJudge(get_sensitive_policy())
    else:
        raise ValueError(f"Unknown judge: {settings.judge}")
    return _judge


def get_recall_engine() -> RecallEngine:
    global _recall
    if _recall:
        return _recall
    settings = get_settings()
    if settings.recall == "keyword":
        _recall = KeywordRecallEngine(get_storage(), get_profile_builder())
    else:
        raise ValueError(f"Unknown recall: {settings.recall}")
    return _recall


def get_event_sink() -> EventSink:
    global _events
    if _events:
        return _events
    settings = get_settings()
    if settings.events == "none":
        _events = NoopEventSink()
    elif settings.events == "ws":
        _events = WebSocketEventSink()
    else:
        raise ValueError(f"Unknown events: {settings.events}")
    return _events
