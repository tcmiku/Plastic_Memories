from typing import Any, List, Optional, Literal

from pydantic import BaseModel


class PersonaCreateRequest(BaseModel):
    user_id: str
    persona_id: str
    display_name: Optional[str] = None
    description: Optional[str] = None


class PersonaProfileResponse(BaseModel):
    user_id: str
    persona_id: str
    profile_markdown: str


class MessageAppendRequest(BaseModel):
    user_id: str
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
    user_id: str
    persona_id: str
    before_ts: Optional[int] = None
    days: Optional[int] = None


MemoryType = Literal["persona", "preferences", "rule", "glossary", "stable_fact"]


class MemoryWriteRequest(BaseModel):
    user_id: str
    persona_id: str
    type: MemoryType
    key: str
    content: str
    tags: Optional[List[str]] = None
    ttl_seconds: Optional[int] = None
    temporary: bool = False
    source_app: Optional[str] = None


class MemoryWriteResponse(BaseModel):
    status: str
    updated: bool = False


class MemoryRecallRequest(BaseModel):
    user_id: str
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
    user_id: str
    persona_id: str
    type: MemoryType
    key: str


class MemoryRebuildRequest(BaseModel):
    user_id: str
    persona_id: str


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
