from typing import Any, List, Optional, Literal

from pydantic import BaseModel


class PersonaCreateRequest(BaseModel):
    persona_id: str
    display_name: Optional[str] = None
    description: Optional[str] = None


class PersonaCreateFromTemplateRequest(BaseModel):
    persona_id: str
    template_path: str
    allow_overwrite: bool = False


class PersonaProfileResponse(BaseModel):
    user_id: str
    persona_id: str
    profile_markdown: str


class PersonaSlotsGetRequest(BaseModel):
    persona_id: str


class PersonaSlotsSetRequest(BaseModel):
    persona_id: str
    slot_name: str
    value_json: Any
    provenance_json: Optional[Any] = None


class MessageAppendRequest(BaseModel):
    persona_id: str
    session_id: Optional[str] = None
    source_app: Optional[str] = None
    role: str
    content: str
    ts: Optional[int] = None


class MessageAppendResponse(BaseModel):
    status: str
    message_id: int


class MessageRecentResponse(BaseModel):
    messages: List[dict]


class MessagePurgeRequest(BaseModel):
    persona_id: str
    before_ts: Optional[int] = None
    days: Optional[int] = None


MemoryType = Literal[
    "persona",
    "preferences",
    "rule",
    "glossary",
    "stable_fact",
    "identity",
    "constraints",
    "values",
    "note",
    "fact",
]
MemoryStatus = Literal["candidate", "active", "revoked", "expired"]
MemoryScope = Literal["session", "app", "persona", "global"]
MemorySourceType = Literal["user_explicit", "model_inferred", "imported", "tool"]
JudgeDecision = Literal["deny", "allow_candidate", "require_confirmation", "allow_active"]


class MemoryWriteRequest(BaseModel):
    persona_id: str
    type: MemoryType
    key: str
    content: str
    tags: Optional[List[str]] = None
    ttl_seconds: Optional[int] = None
    temporary: bool = False
    source_app: Optional[str] = None
    scope: MemoryScope = "persona"
    source_type: MemorySourceType = "user_explicit"
    source_ref: Optional[str] = None
    confidence: Optional[float] = None
    expires_at: Optional[int] = None
    supersedes_id: Optional[int] = None


class MemoryWriteResponse(BaseModel):
    status: str
    updated: bool = False
    memory_id: Optional[int] = None
    memory_status: Optional[MemoryStatus] = None


class MemoryRecallRequest(BaseModel):
    persona_id: str
    query: str
    limit: int = 10


class MemoryRecallResponse(BaseModel):
    PERSONA_PROFILE: str
    PERSONA_MEMORY: List[dict]
    CHAT_SNIPPETS: List[dict]


class MemoryListResponse(BaseModel):
    items: List[dict]


class MemoryForgetRequest(BaseModel):
    persona_id: str
    type: MemoryType
    key: str


class MemoryRebuildRequest(BaseModel):
    persona_id: str


class MemoryConfirmRequest(BaseModel):
    persona_id: str
    memory_id: int
    supersedes_id: Optional[int] = None


class MemoryRevokeRequest(BaseModel):
    persona_id: str
    memory_id: int


class HealthResponse(BaseModel):
    status: str
    db_path: str


class CapabilitiesResponse(BaseModel):
    backend: str
    recall: str
    judge: str
    profile: str
    sensitive: str
    events: str
    memory_types: List[str]


class MetricsResponse(BaseModel):
    personas: int
    messages: int
    memory_items: int


class ErrorResponse(BaseModel):
    detail: Any


GoalStatus = Literal["active", "paused", "done"]


class GoalCreateRequest(BaseModel):
    persona_id: str
    title: str
    details: Optional[str] = None


class GoalUpdateStatusRequest(BaseModel):
    persona_id: str
    goal_id: int
    status: GoalStatus


class GoalLinkRequest(BaseModel):
    persona_id: str
    goal_id: int
    memory_id: Optional[int] = None
    note: Optional[str] = None
