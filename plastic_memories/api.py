import json
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse

from .config import get_settings
from .context import set_request_context
from .auth import AuthedUser, require_user
from .http import ok, fail
from .logging import configure_logging, log_event
from .templates import resolve_template_path, load_persona_template
from .schemas import (
    PersonaCreateRequest,
    PersonaCreateFromTemplateRequest,
    MessageAppendRequest,
    MessagePurgeRequest,
    MemoryWriteRequest,
    MemoryRecallRequest,
    MemoryForgetRequest,
    MemoryRebuildRequest,
    MemoryConfirmRequest,
    MemoryRevokeRequest,
    PersonaSlotsGetRequest,
    PersonaSlotsSetRequest,
    GoalCreateRequest,
    GoalUpdateStatusRequest,
    GoalLinkRequest,
)

from .utils import gen_request_id, now_ts, dumps_json
from .ext.registry import get_storage, get_recall_engine, get_judge, get_event_sink
from .ext.recall.keyword import build_profile_from_slots

app = FastAPI(title="Plastic Memories", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    configure_logging()
    get_storage()


def _extract_persona_from_body(request: Request) -> str | None:
    return request.query_params.get("persona_id")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or gen_request_id()
    persona_id = _extract_persona_from_body(request)
    if not persona_id:
        try:
            body = await request.body()
            if body:
                payload = json.loads(body.decode("utf-8"))
                if isinstance(payload, dict):
                    persona_id = payload.get("persona_id")
        except Exception:
            pass
    set_request_context(request_id, user_id=None, persona_id=persona_id)
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
        content=fail("http_error", "请求错误", detail=exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    log_event("api.error")
    return JSONResponse(
        status_code=422,
        content=fail("validation_error", "参数校验失败", detail=exc.errors()),
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    log_event("api.error")
    return JSONResponse(status_code=500, content=fail("internal_error", "内部错误", detail=None))


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
def persona_create(payload: PersonaCreateRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    storage.create_persona(user.user_id, payload.persona_id, payload.display_name, payload.description)
    return ok({"status": "ok"})


@app.post("/persona/create_from_template", response_model=None)
def persona_create_from_template(payload: PersonaCreateFromTemplateRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    try:
        template_dir = resolve_template_path(payload.template_path)
        seed = load_persona_template(template_dir)
        log_event(
            "persona.template.load",
            user_id=user.user_id,
            persona_id=payload.persona_id,
            template_path=payload.template_path,
        )
    except json.JSONDecodeError as exc:
        log_event(
            "persona.template.error",
            user_id=user.user_id,
            persona_id=payload.persona_id,
            template_path=payload.template_path,
        )
        return JSONResponse(
            status_code=422,
            content=fail("validation_error", "preferences.json 解析失败", detail=str(exc)),
        )
    except Exception as exc:
        log_event(
            "persona.template.error",
            user_id=user.user_id,
            persona_id=payload.persona_id,
            template_path=payload.template_path,
        )
        raise HTTPException(status_code=400, detail={"reason": str(exc)})

    storage.create_persona(user.user_id, payload.persona_id, None, None)
    existing = storage.list_memory(user.user_id, payload.persona_id)
    existing_keys = {(item.get("type"), item.get("mkey")) for item in existing}

    to_write: list[dict] = []
    persona_md = seed.persona_md or ""
    rules_md = seed.rules_md or ""
    preferences_json = seed.preferences_json or {}

    def should_write(mtype: str, key: str) -> bool:
        if payload.allow_overwrite:
            return True
        return (mtype, key) not in existing_keys

    if should_write("persona", "persona_md"):
        to_write.append({"type": "persona", "key": "persona_md", "content": persona_md})
    if should_write("rule", "rules_md") and (payload.allow_overwrite or rules_md):
        to_write.append({"type": "rule", "key": "rules_md", "content": rules_md})
    if should_write("preferences", "preferences_json") and (payload.allow_overwrite or preferences_json):
        to_write.append({"type": "preferences", "key": "preferences_json", "content": json.dumps(preferences_json, ensure_ascii=False)})

    applied = bool(to_write)
    skipped = not applied and not payload.allow_overwrite
    overwritten = payload.allow_overwrite and applied

    for item in to_write:
        decision = get_judge().judge({
            "user_id": user.user_id,
            "persona_id": payload.persona_id,
            "content": item["content"],
            "source_type": "user_explicit",
        })
        if decision["decision"] == "deny":
            raise HTTPException(status_code=400, detail=fail("judge_deny", "Rejected", detail=decision.get("reason")))
        status = "active"
        if decision["decision"] in ("allow_candidate", "require_confirmation"):
            status = "candidate"
        storage.write_memory({
            "user_id": user.user_id,
            "persona_id": payload.persona_id,
            "type": item["type"],
            "key": item["key"],
            "content": item["content"],
            "tags": [],
            "ttl_seconds": None,
            "status": status,
            "source_type": "user_explicit",
        })

    event = "persona.template.apply"
    if skipped:
        event = "persona.template.skip"
    log_event(
        event,
        user_id=user.user_id,
        persona_id=payload.persona_id,
        template_path=payload.template_path,
    )

    return ok({
        "user_id": user.user_id,
        "persona_id": payload.persona_id,
        "template_path": payload.template_path,
        "applied": applied,
        "skipped": skipped,
        "overwritten": overwritten,
        "seed": {
            "persona_md_len": len(persona_md),
            "rules_md_len": len(rules_md),
            "preferences_keys": list(preferences_json.keys()),
        },
    })


@app.get("/persona/profile", response_model=None)
def persona_profile(persona_id: str, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    persona = storage.get_persona(user.user_id, persona_id)
    settings = get_settings()
    slots = storage.get_slots(user.user_id, persona_id)
    profile = build_profile_from_slots(persona, slots, settings.profile_max_chars)
    return ok({"user_id": user.user_id, "persona_id": persona_id, "profile_markdown": profile})


@app.post("/messages/append", response_model=None)
def messages_append(payload: MessageAppendRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    created_at = payload.ts or now_ts()
    msg_id = storage.append_message({**payload.model_dump(), "user_id": user.user_id, "created_at": created_at})
    return ok({"status": "ok", "message_id": msg_id})


@app.get("/messages/recent", response_model=None)
def messages_recent(persona_id: str, limit: int = 20, days: int | None = None, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    messages = storage.recent_messages(user.user_id, persona_id, limit, days)
    return ok({"messages": messages})


@app.post("/messages/purge", response_model=None)
def messages_purge(payload: MessagePurgeRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    before_ts = payload.before_ts
    if before_ts is None and payload.days is not None:
        before_ts = now_ts() - payload.days * 86400
    deleted = storage.purge_messages(user.user_id, payload.persona_id, before_ts)
    return ok({"status": "ok", "deleted": deleted})


@app.post("/memory/write", response_model=None)
def memory_write(payload: MemoryWriteRequest, user: AuthedUser = Depends(require_user)):
    if payload.temporary:
        return ok({"status": "skipped", "updated": False})
    judge = get_judge()
    decision = judge.judge({**payload.model_dump(), "user_id": user.user_id})
    if decision["decision"] == "deny":
        return JSONResponse(
            status_code=400,
            content=fail("judge_deny", "Rejected", detail=decision.get("reason")),
        )
    storage = get_storage()
    status = "active"
    if decision["decision"] in ("allow_candidate", "require_confirmation"):
        status = "candidate"
    slot_types = {"identity", "constraints", "values", "preferences"}
    if payload.type in slot_types:
        status = "candidate"
    updated, mem_id = storage.write_memory({**payload.model_dump(), "user_id": user.user_id, "status": status})
    get_event_sink().emit("memory.write", {**payload.model_dump(), "user_id": user.user_id})
    return ok({"status": "ok", "updated": updated, "memory_id": mem_id, "memory_status": status})


@app.post("/memory/recall", response_model=None)
def memory_recall(payload: MemoryRecallRequest, user: AuthedUser = Depends(require_user)):
    recall_engine = get_recall_engine()
    result = recall_engine.recall(user.user_id, payload.persona_id, payload.query, payload.limit)
    return ok(result)


@app.get("/memory/list", response_model=None)
def memory_list(persona_id: str, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    return ok({"items": storage.list_memory(user.user_id, persona_id)})


@app.post("/memory/forget", response_model=None)
def memory_forget(payload: MemoryForgetRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    deleted = storage.forget_memory(user.user_id, payload.persona_id, payload.type, payload.key)
    return ok({"status": "ok", "deleted": deleted})


@app.post("/memory/rebuild", response_model=None)
def memory_rebuild(payload: MemoryRebuildRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    storage.rebuild_fts(user.user_id, payload.persona_id)
    return ok({"status": "ok"})


@app.post("/memory/confirm", response_model=None)
def memory_confirm(payload: MemoryConfirmRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    result = storage.confirm_memory(user.user_id, payload.persona_id, payload.memory_id, payload.supersedes_id)
    if not result:
        raise HTTPException(status_code=404, detail="Memory not found")
    if result.get("error") == "conflict_requires_supersedes":
        return JSONResponse(
            status_code=409,
            content=fail("conflict_requires_supersedes", "Conflict requires supersedes_id", detail=None),
        )
    if result["updated"] and result["status"] == "active":
        memory = storage.get_memory_by_id(user.user_id, payload.persona_id, payload.memory_id)
        if memory and memory.get("type") in ("identity", "constraints", "values", "preferences"):
            value_json = dumps_json({"text": memory.get("content")})
            superseded = payload.supersedes_id or memory.get("supersedes_id")
            provenance_json = dumps_json({
                "source": "memory_confirm",
                "active_memory_id": payload.memory_id,
                "superseded": superseded,
            })
            storage.set_slot(user.user_id, payload.persona_id, memory["type"], value_json, provenance_json)
    return ok({"status": "ok", "updated": result["updated"], "memory_status": result["status"]})


@app.post("/memory/revoke", response_model=None)
def memory_revoke(payload: MemoryRevokeRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    result = storage.revoke_memory(user.user_id, payload.persona_id, payload.memory_id)
    if not result:
        raise HTTPException(status_code=404, detail="Memory not found")
    return ok({"status": "ok", "updated": result["updated"], "memory_status": result["status"]})


@app.post("/persona/slots/get", response_model=None)
def persona_slots_get(payload: PersonaSlotsGetRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    slots = storage.get_slots(user.user_id, payload.persona_id)
    return ok({"items": slots})


@app.post("/persona/slots/set", response_model=None)
def persona_slots_set(payload: PersonaSlotsSetRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    value_json = dumps_json(payload.value_json)
    provenance_json = dumps_json(payload.provenance_json) if payload.provenance_json is not None else None
    storage.set_slot(user.user_id, payload.persona_id, payload.slot_name, value_json, provenance_json)
    return ok({"status": "ok"})


@app.post("/goals/create", response_model=None)
def goals_create(payload: GoalCreateRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    goal_id = storage.create_goal(user.user_id, payload.persona_id, payload.title, payload.details)
    return ok({"status": "ok", "goal_id": goal_id})


@app.get("/goals/list", response_model=None)
def goals_list(persona_id: str, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    items = storage.list_goals(user.user_id, persona_id)
    return ok({"items": items})


@app.post("/goals/update_status", response_model=None)
def goals_update_status(payload: GoalUpdateStatusRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    updated = storage.update_goal_status(user.user_id, payload.persona_id, payload.goal_id, payload.status)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return ok({"status": "ok", "updated": updated})


@app.post("/goals/link", response_model=None)
def goals_link(payload: GoalLinkRequest, user: AuthedUser = Depends(require_user)):
    storage = get_storage()
    link_id = storage.link_goal(user.user_id, payload.persona_id, payload.goal_id, payload.memory_id, payload.note)
    if link_id is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return ok({"status": "ok", "link_id": link_id})


@app.post("/_test/boom", response_model=None)
def _test_boom(user: AuthedUser = Depends(require_user)):
    raise RuntimeError("boom")
