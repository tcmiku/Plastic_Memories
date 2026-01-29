from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse

from .config import get_settings
from .context import set_request_context
from .http import ok, fail
from .logging import configure_logging, log_event
from .schemas import (
    PersonaCreateRequest,
    MessageAppendRequest,
    MessagePurgeRequest,
    MemoryWriteRequest,
    MemoryRecallRequest,
    MemoryForgetRequest,
    MemoryRebuildRequest,
)
import time

from .utils import gen_request_id, now_ts
from .ext.registry import get_storage, get_recall_engine, get_judge, get_profile_builder, get_event_sink

app = FastAPI(title="Plastic Memories", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    configure_logging()
    get_storage()


def _extract_context_from_body(request: Request) -> tuple[str | None, str | None]:
    user_id = request.query_params.get("user_id")
    persona_id = request.query_params.get("persona_id")
    return user_id, persona_id


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or gen_request_id()
    user_id, persona_id = _extract_context_from_body(request)
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
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((time.time() - start) * 1000)
        log_event("api.request", path=request.url.path, status=500, duration_ms=duration_ms, request_id=request_id)
        raise
    duration_ms = int((time.time() - start) * 1000)
    log_event("api.request", path=request.url.path, status=response.status_code, duration_ms=duration_ms, request_id=request_id)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    log_event("api.error")
    return JSONResponse(
        status_code=exc.status_code,
        content=fail("http_error", "请求错误", details=exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    log_event("api.error")
    return JSONResponse(
        status_code=422,
        content=fail("validation_error", "参数校验失败", details=exc.errors()),
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    log_event("api.error")
    return JSONResponse(status_code=500, content=fail("internal_error", "内部错误", details=None))


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


@app.get("/health", response_model=None)
def health():
    settings = get_settings()
    return ok({"status": "ok", "db_path": str(settings.db_path)})


@app.get("/capabilities", response_model=None)
def capabilities():
    settings = get_settings()
    return ok({
        "backend": settings.backend,
        "recall": settings.recall,
        "judge": settings.judge,
        "profile": settings.profile,
        "sensitive": settings.sensitive,
        "events": settings.events,
        "memory_types": ["persona", "preferences", "rule", "glossary", "stable_fact"],
    })


@app.get("/metrics", response_model=None)
def metrics():
    storage = get_storage()
    return ok(storage.metrics())


@app.post("/persona/create", response_model=None)
def persona_create(payload: PersonaCreateRequest):
    storage = get_storage()
    storage.create_persona(payload.user_id, payload.persona_id, payload.display_name, payload.description)
    return ok({"status": "ok"})


@app.get("/persona/profile", response_model=None)
def persona_profile(user_id: str, persona_id: str):
    storage = get_storage()
    persona = storage.get_persona(user_id, persona_id)
    profile_builder = get_profile_builder()
    profile = profile_builder.build(persona, storage.list_memory(user_id, persona_id))
    return ok({"user_id": user_id, "persona_id": persona_id, "profile_markdown": profile})


@app.post("/messages/append", response_model=None)
def messages_append(payload: MessageAppendRequest):
    storage = get_storage()
    created_at = payload.ts or now_ts()
    msg_id = storage.append_message({**payload.model_dump(), "created_at": created_at})
    return ok({"status": "ok", "message_id": msg_id})


@app.get("/messages/recent", response_model=None)
def messages_recent(user_id: str, persona_id: str, limit: int = 20, days: int | None = None):
    storage = get_storage()
    messages = storage.recent_messages(user_id, persona_id, limit, days)
    return ok({"messages": messages})


@app.post("/messages/purge", response_model=None)
def messages_purge(payload: MessagePurgeRequest):
    storage = get_storage()
    before_ts = payload.before_ts
    if before_ts is None and payload.days is not None:
        before_ts = now_ts() - payload.days * 86400
    deleted = storage.purge_messages(payload.user_id, payload.persona_id, before_ts)
    return ok({"status": "ok", "deleted": deleted})


@app.post("/memory/write", response_model=None)
def memory_write(payload: MemoryWriteRequest):
    if payload.temporary:
        return ok({"status": "skipped", "updated": False})
    judge = get_judge()
    decision = judge.judge(payload.model_dump())
    if not decision["allow"]:
        raise HTTPException(status_code=400, detail={"reason": decision["reason"]})
    storage = get_storage()
    updated, _ = storage.write_memory(payload.model_dump())
    get_event_sink().emit("memory.write", payload.model_dump())
    return ok({"status": "ok", "updated": updated})


@app.post("/memory/recall", response_model=None)
def memory_recall(payload: MemoryRecallRequest):
    recall_engine = get_recall_engine()
    result = recall_engine.recall(payload.user_id, payload.persona_id, payload.query, payload.limit)
    return ok(result)


@app.get("/memory/list", response_model=None)
def memory_list(user_id: str, persona_id: str):
    storage = get_storage()
    return ok({"items": storage.list_memory(user_id, persona_id)})


@app.post("/memory/forget", response_model=None)
def memory_forget(payload: MemoryForgetRequest):
    storage = get_storage()
    deleted = storage.forget_memory(payload.user_id, payload.persona_id, payload.type, payload.key)
    return ok({"status": "ok", "deleted": deleted})


@app.post("/memory/rebuild", response_model=None)
def memory_rebuild(payload: MemoryRebuildRequest):
    storage = get_storage()
    storage.rebuild_fts(payload.user_id, payload.persona_id)
    return ok({"status": "ok"})
