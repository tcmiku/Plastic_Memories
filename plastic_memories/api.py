from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse

from .config import get_settings
from .context import set_request_context
from .logging import configure_logging, log_event
from .schemas import (
    PersonaCreateRequest,
    PersonaProfileResponse,
    MessageAppendRequest,
    MessageAppendResponse,
    MessageRecentResponse,
    MessagePurgeRequest,
    MemoryWriteRequest,
    MemoryWriteResponse,
    MemoryRecallRequest,
    MemoryRecallResponse,
    MemoryListResponse,
    MemoryForgetRequest,
    MemoryRebuildRequest,
    HealthResponse,
    CapabilitiesResponse,
    MetricsResponse,
)
from .utils import gen_request_id, now_ts
from .ext.registry import get_storage, get_recall_engine, get_judge, get_profile_builder, get_event_sink

app = FastAPI(title="Plastic Memories", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    configure_logging()
    get_storage()


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or gen_request_id()
    user_id = request.query_params.get("user_id")
    persona_id = request.query_params.get("persona_id")
    if not user_id or not persona_id:
        try:
            body = await request.body()
            if body:
                import json

                payload = json.loads(body.decode("utf-8"))
                if isinstance(payload, dict):
                    user_id = user_id or payload.get("user_id")
                    persona_id = persona_id or payload.get("persona_id")
        except Exception:
            pass
    set_request_context(request_id, user_id=user_id, persona_id=persona_id)
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    log_event("api.error")
    return JSONResponse(status_code=500, content={"detail": "internal_error"})


@app.get("/health", response_model=HealthResponse)
def health():
    settings = get_settings()
    return {"status": "ok", "db_path": str(settings.db_path)}


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Plastic Memories API</title>
        <style>
          :root { color-scheme: light; }
          body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif; margin: 40px; color: #1f2328; }
          h1 { margin-bottom: 8px; }
          p { margin-top: 0; color: #5a6472; }
          .card { border: 1px solid #e6e8eb; border-radius: 12px; padding: 16px 20px; margin: 16px 0; }
          ul { margin: 8px 0 0 18px; }
          code { background: #f6f8fa; padding: 2px 6px; border-radius: 6px; }
          a { color: #0b6cff; text-decoration: none; }
          a:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <h1>Plastic Memories API</h1>
        <p>欢迎使用人格与长期记忆中枢。请通过以下入口查看接口与调试。</p>
        <div class="card">
          <strong>API 文档</strong>
          <ul>
            <li><a href="/docs">Swagger UI</a></li>
            <li><a href="/redoc">ReDoc</a></li>
            <li><a href="/openapi.json">OpenAPI JSON</a></li>
          </ul>
        </div>
        <div class="card">
          <strong>基础接口</strong>
          <ul>
            <li><code>GET /health</code> 健康检查</li>
            <li><code>GET /capabilities</code> 当前能力与实现</li>
            <li><code>GET /metrics</code> 统计信息</li>
          </ul>
        </div>
        <div class="card">
          <strong>示例请求</strong>
          <ul>
            <li>查看 <code>examples/requests.http</code></li>
          </ul>
        </div>
      </body>
    </html>
    """


@app.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities():
    settings = get_settings()
    return {
        "backend": settings.backend,
        "recall": settings.recall,
        "judge": settings.judge,
        "profile": settings.profile,
        "sensitive": settings.sensitive,
        "events": settings.events,
        "memory_types": ["persona", "preferences", "rule", "glossary", "stable_fact"],
    }


@app.get("/metrics", response_model=MetricsResponse)
def metrics():
    storage = get_storage()
    return storage.metrics()


@app.post("/persona/create", response_model=None)
def persona_create(payload: PersonaCreateRequest):
    storage = get_storage()
    storage.create_persona(payload.user_id, payload.persona_id, payload.display_name, payload.description)
    return {"status": "ok"}


@app.get("/persona/profile", response_model=PersonaProfileResponse)
def persona_profile(user_id: str, persona_id: str):
    storage = get_storage()
    persona = storage.get_persona(user_id, persona_id)
    profile_builder = get_profile_builder()
    profile = profile_builder.build(persona, storage.list_memory(user_id, persona_id))
    return {"user_id": user_id, "persona_id": persona_id, "profile_markdown": profile}


@app.post("/messages/append", response_model=MessageAppendResponse)
def messages_append(payload: MessageAppendRequest):
    storage = get_storage()
    created_at = payload.ts or now_ts()
    msg_id = storage.append_message({**payload.model_dump(), "created_at": created_at})
    return {"status": "ok", "message_id": msg_id}


@app.get("/messages/recent", response_model=MessageRecentResponse)
def messages_recent(user_id: str, persona_id: str, limit: int = 20, days: int | None = None):
    storage = get_storage()
    messages = storage.recent_messages(user_id, persona_id, limit, days)
    return {"messages": messages}


@app.post("/messages/purge", response_model=None)
def messages_purge(payload: MessagePurgeRequest):
    storage = get_storage()
    before_ts = payload.before_ts
    if before_ts is None and payload.days is not None:
        before_ts = now_ts() - payload.days * 86400
    deleted = storage.purge_messages(payload.user_id, payload.persona_id, before_ts)
    return {"status": "ok", "deleted": deleted}


@app.post("/memory/write", response_model=MemoryWriteResponse)
def memory_write(payload: MemoryWriteRequest):
    if payload.temporary:
        return {"status": "skipped", "updated": False}
    judge = get_judge()
    decision = judge.judge(payload.model_dump())
    if not decision["allow"]:
        raise HTTPException(status_code=400, detail={"reason": decision["reason"]})
    storage = get_storage()
    updated, _ = storage.write_memory(payload.model_dump())
    get_event_sink().emit("memory.write", payload.model_dump())
    return {"status": "ok", "updated": updated}


@app.post("/memory/recall", response_model=MemoryRecallResponse)
def memory_recall(payload: MemoryRecallRequest):
    recall_engine = get_recall_engine()
    result = recall_engine.recall(payload.user_id, payload.persona_id, payload.query, payload.limit)
    return result


@app.get("/memory/list", response_model=MemoryListResponse)
def memory_list(user_id: str, persona_id: str):
    storage = get_storage()
    return {"items": storage.list_memory(user_id, persona_id)}


@app.post("/memory/forget", response_model=None)
def memory_forget(payload: MemoryForgetRequest):
    storage = get_storage()
    deleted = storage.forget_memory(payload.user_id, payload.persona_id, payload.type, payload.key)
    return {"status": "ok", "deleted": deleted}


@app.post("/memory/rebuild", response_model=None)
def memory_rebuild(payload: MemoryRebuildRequest):
    storage = get_storage()
    storage.rebuild_fts(payload.user_id, payload.persona_id)
    return {"status": "ok"}
