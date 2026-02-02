# Plastic Memories

跨应用、可扩展的 AI 人格与长期记忆系统。该项目提供稳定的人格与记忆中枢，可通过 HTTP/WS 插件被桌面宠物、CLI、IDE 插件、Web 应用等共享接入。

## 功能特性
- 人格与记忆独立于任何 UI
- 通过 `user_id + persona_id` 共享同一人格
- 保留有限聊天原文片段以增强连续感
- SQLite 持久化（WSL/Linux 友好）
- 严格单元测试与合同测试
- 可插拔架构：存储、召回、裁决、画像、敏感策略、事件

## 核心概念
- `user_id`：用户身份
- `persona_id`：人格身份（例如 default / work / pet / vtuber）
- `session_id`：一次会话的会话标识
- `source_app`：来源应用（例如 tools_live2D / cli / ide / web）

## 数据模型（必备表）
- `personas`：人格基本信息
- `messages`：聊天原文（有限留存）
- `memory_items`：人格/偏好/规则/稳定事实
- `meta`：内部元信息（如 FTS 启用状态）
- `fts_messages` / `fts_memory`：可选 FTS5 全文索引（支持降级）

`memory_items.type` 允许的类型：
- `persona`
- `preferences`
- `rule`
- `glossary`
- `stable_fact`

## 快速开始

```bash
pip install -r requirements.txt
uvicorn plastic_memories.api:app --host 0.0.0.0 --port 8007
```

## 配置说明（环境变量）

核心切换：
- `PLASTIC_MEMORIES_BACKEND=sqlite`
- `PLASTIC_MEMORIES_RECALL=keyword`
- `PLASTIC_MEMORIES_JUDGE=rules`
- `PLASTIC_MEMORIES_PROFILE=markdown`
- `PLASTIC_MEMORIES_SENSITIVE=strict`
- `PLASTIC_MEMORIES_EVENTS=none|ws`

存储与日志：
- `PLASTIC_MEMORIES_DB_PATH`：数据库文件路径
- `PLASTIC_MEMORIES_LOG_DIR`：日志目录
- `PLASTIC_MEMORIES_LOG_LEVEL`：日志级别（默认 INFO）
- `LOG_PATH`：日志文件完整路径（优先级高于目录）
- `PLASTIC_MEMORIES_BUSY_TIMEOUT_MS`：SQLite busy_timeout（毫秒）
- `PLASTIC_MEMORIES_TEMPLATE_ROOT`：人格模板根目录（默认 `<repo_root>/personas`）

召回与片段：
- `PLASTIC_MEMORIES_SNIPPET_DAYS`：聊天片段天数（默认 7）
- `PLASTIC_MEMORIES_SNIPPET_LIMIT`：片段数量上限（默认 20）

## Linux 服务器部署

1. 创建虚拟环境并安装依赖。
2. 设置必要的环境变量（见下文）。
3. 使用 systemd 或进程管理器启动。示例 systemd 配置：

```ini
[Unit]
Description=Plastic Memories API
After=network.target

[Service]
User=pmem
WorkingDirectory=/opt/plastic_memories
Environment=PLASTIC_MEMORIES_DB_PATH=/var/lib/plastic_memories/plastic_memories.db
Environment=PLASTIC_MEMORIES_LOG_DIR=/var/log/plastic_memories
ExecStart=/opt/plastic_memories/.venv/bin/uvicorn plastic_memories.api:app --host 0.0.0.0 --port 8007
Restart=always

[Install]
WantedBy=multi-user.target
```

## 实现切换（可插拔）

通过环境变量切换实现：

```bash
export PLASTIC_MEMORIES_BACKEND=sqlite
export PLASTIC_MEMORIES_RECALL=keyword
export PLASTIC_MEMORIES_JUDGE=rules
export PLASTIC_MEMORIES_PROFILE=markdown
export PLASTIC_MEMORIES_SENSITIVE=strict
export PLASTIC_MEMORIES_EVENTS=none
```

## 数据库与日志路径

数据库默认路径：
- Linux/macOS：`~/.plastic_memories/plastic_memories.db`
- Windows：`%APPDATA%/PlasticMemories/plastic_memories.db`
- 可用 `PLASTIC_MEMORIES_DB_PATH` 覆盖

日志默认路径：
- Linux/macOS：`~/.plastic_memories/logs`
- Windows：`%APPDATA%/PlasticMemories/logs`
- 可用 `PLASTIC_MEMORIES_LOG_DIR` 覆盖

## 数据库迁移（服务器迁移参考）

1. **确认数据库文件位置**  
   - 默认路径见上文，或检查是否设置了 `PLASTIC_MEMORIES_DB_PATH`。  
2. **停服务后复制数据库文件**  
   - 建议先停止服务，复制 `plastic_memories.db`（如需也可同步日志目录）。  
3. **新服务器恢复**  
   - 将数据库文件放到目标路径（默认或 `PLASTIC_MEMORIES_DB_PATH` 指定位置）。  
4. **启动并验证**  
   - 启动服务后请求 `GET /health`，确认 `db_path` 指向期望路径。  

常见注意事项：  
- 若跨平台迁移（Windows → Linux/反之），确保路径格式正确且有读写权限。  
- SQLite 为单文件，迁移时务必保证源端不在写入（避免损坏）。  
- 如有自定义 `PLASTIC_MEMORIES_TEMPLATE_ROOT`，也可一并迁移模板目录。

## 日志与追踪

日志为 JSON 结构化输出，包含以下字段：
- `ts`：时间戳（ISO8601）
- `level`：日志级别
- `event`：事件名称
- `logger`：记录器名称
- `msg`：日志消息
- `request_id`：请求追踪 ID（支持 `X-Request-Id`）
- `user_id` / `persona_id`：业务上下文
- `duration_ms`：耗时（如有）
- `err`：异常信息（如有）

关键事件示例：
- `db.init`
- `db.migrate`
- `messages.append`
- `memory.write`
- `memory.recall`
- `fts.fallback`
- `api.request`
- `api.error`

## 运行测试与覆盖率

```bash
pytest -q
pytest --cov=plastic_memories --cov-report=term-missing
pytest -q tests/client_contract
```

### Windows + pytest-cov 临时目录说明

为了避免 Windows 上 pytest-cov 在系统临时目录写入失败，本仓库提供 `sitecustomize.py`：
- 仅在检测到 pytest/coverage 环境时生效（`PYTEST_CURRENT_TEST` 或 `pytest` 参数，或覆盖率相关环境变量）
- 将覆盖率文件与临时目录固定到仓库内的 `.test_tmp/`
- 非测试运行时保持 no-op，不影响服务启动与运行

## API 一览

- `GET /health`
- `GET /capabilities`
- `GET /metrics`
- `POST /persona/create`
- `POST /persona/create_from_template`
- `GET /persona/profile`
- `POST /messages/append`
- `GET /messages/recent`
- `POST /messages/purge`
- `POST /memory/write`
- `POST /memory/recall`
- `GET /memory/list`
- `POST /memory/forget`
- `POST /memory/rebuild`

示例请求见 `examples/requests.http`。

## API Contract & Examples

### 基础信息
- Base URL（本地示例）：`http://127.0.0.1:8007`
- Header：`X-API-Key: <key>`
- 环境变量示例：
  - `PLASTIC_MEMORIES_API_KEYS="devkey:userA,devkey2:userB"`

### 统一响应 Envelope
- 成功：
  - `{"ok": true, "request_id": "<id>", "data": {...}}`
- 失败：
  - `{"ok": false, "request_id": "<id>", "error": {"code": "<string>", "message": "<string>", "detail": <any>}}`

### 记忆模型关键字段
- `status`: candidate | active | revoked | expired
- `scope`: session | app | persona | global
- `source_type`: user_explicit | model_inferred | imported | tool
- `expires_at`: epoch seconds（int）
- `supersedes_id`: 覆盖链指向旧 active 的 memory_id

### Slots 映射规则（身份一致性）
- slot 类型集合：`identity` / `constraints` / `values` / `preferences`
- 这些类型写入一律 candidate，必须 confirm
- confirm 冲突规则：
  - 若该 type 已有 active：
    - 未提供 `supersedes_id` → `409 conflict_requires_supersedes`
    - `supersedes_id` 不是当前 active → `409 conflict_requires_supersedes`
    - `supersedes_id` 合法 → 旧 active → revoked，新 → active，slots 更新
- slots provenance 字段：
  - `active_memory_id`：当前 active 的 memory_id
  - `superseded`：被覆盖的 memory_id（可能为 null）

### revoke vs forget（软撤销 vs 硬删除）
- revoke：软撤销，`status=revoked`；不物理删除、不删 FTS rowid；list/recall 过滤掉
- forget：硬删除，删除 `memory_items` 行并删除 `fts_memory` rowid；get_by_id 为 None（或 404）

### goals 最小流程
- `POST /goals/create` → `goal_id`
- `GET /goals/list` → `items`
- `POST /goals/update_status` → `updated`
- `POST /goals/link` → `link_id`

### 读隔离说明
- `user_id` 由 `X-API-Key` 派生，客户端不得传 `user_id`
- 不同 user 之间无法 list/recall/profile/slots 读取彼此数据
- 当前实现策略：请求成功但返回空列表/空内容（无跨租户泄露）

### 可复制 curl 示例

**准备**
```bash
export API_KEY=devkey
export BASE_URL=http://127.0.0.1:8007
```

**E1) memory/write（slot 类型写入 → candidate）**
```bash
curl -s $BASE_URL/memory/write \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","type":"identity","key":"id1","content":"dev","source_type":"user_explicit"}'
```
预期：`ok=true`，`data.memory_status="candidate"`，包含 `memory_id`

**E2) memory/confirm（无冲突 → active + slot 更新）**
```bash
curl -s $BASE_URL/memory/confirm \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","memory_id": 1}'
```
预期：`ok=true`，`data.memory_status="active"`

**E3) 冲突 confirm（缺 supersedes_id → 409）**
```bash
curl -s -o /dev/null -w "%{http_code}\n" $BASE_URL/memory/confirm \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","memory_id": 2}'
```
预期：HTTP 409，`error.code="conflict_requires_supersedes"`

**E4) supersedes 覆盖（带 supersedes_id）**
```bash
curl -s $BASE_URL/memory/confirm \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","memory_id": 2, "supersedes_id": 1}'
```
预期：`ok=true`；旧 active 变 revoked，新 active 生效，slots 更新

**E5) revoke 与 forget**
```bash
curl -s $BASE_URL/memory/revoke \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","memory_id": 2}'
curl -s $BASE_URL/memory/forget \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","type":"preferences","key":"pref-x"}'
```
预期：revoke 后主表仍存在但 list/recall 不返回；forget 后主表删除且不召回

**E6) persona/slots/get**
```bash
curl -s $BASE_URL/persona/slots/get \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"persona_id":"p1"}'
```
预期：包含 `items`，slot 更新可见

**E7) goals 流程**
```bash
curl -s $BASE_URL/goals/create \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","title":"Learn Rust","details":"practice"}'
curl -s "$BASE_URL/goals/list?persona_id=p1" -H "X-API-Key: $API_KEY"
curl -s $BASE_URL/goals/update_status \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","goal_id": 1,"status":"done"}'
curl -s $BASE_URL/goals/link \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"persona_id":"p1","goal_id": 1,"memory_id": null,"note":"start"}'
```
预期：返回 `goal_id` / `items` / `updated` / `link_id`

**E8) 401 / 422 错误示例**
```bash
curl -s $BASE_URL/memory/write -H "Content-Type: application/json" -d '{}'
curl -s $BASE_URL/memory/write -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{"persona_id":"p1"}'
```
预期：`ok=false` 且包含统一 error envelope

## 召回返回格式

`POST /memory/recall` 返回字段：
- `PERSONA_PROFILE`：人格画像（Markdown）
- `PERSONA_MEMORY`：相关记忆条目
- `CHAT_SNIPPETS`：近期聊天片段

## 官方 Python SDK

SDK 位置：`clients/python/plastic_memories_client`

安装方式（仓库内使用）：

```bash
python -c "from clients.python.plastic_memories_client import PlasticMemoriesClient; print(PlasticMemoriesClient)"
```

最小示例（召回注入 + 追加 + 写入）：

```python
from clients.python.plastic_memories_client import PlasticMemoriesClient, Message

client = PlasticMemoriesClient(base_url="http://127.0.0.1:8007", user_id="local", persona_id="default")

recall = client.recall("请总结我喜欢的回答风格")
print(recall.injection_block)

client.append_messages([
    Message(role="user", content="请用默认中文"),
    Message(role="user", content="回答工程化"),
])

client.write([
    Message(role="user", content="叫我 tcmiku"),
])
```

与 tools_live2D 接入建议：
1. 聊天前先 `recall()`，将 `injection_block` 注入系统提示。
2. 聊天后将对话追加：`append_messages()`。
3. 对需要长期保存的偏好再 `write()`。
4. 如果需要初始化人格模板，可调用 `create_from_template()`。

SDK 契约测试（无需启动服务）：

```bash
pytest -q tests/client_contract
```

示例脚本：`examples/client_sdk_demo.py`（真实 HTTP，需要先启动服务）。

## 扩展实现指南（建议）

所有核心能力均通过接口抽象（Protocol）实现，可替换扩展：
- `StorageBackend`：持久化后端（默认 SQLite）
- `RecallEngine`：召回引擎（默认 Keyword/FTS）
- `JudgeEngine`：裁决引擎（默认 RuleBased）
- `ProfileBuilder`：画像构建（默认 Markdown）
- `SensitivePolicy`：敏感策略（默认 StrictDeny）
- `EventSink`：事件输出（默认 Noop / WS）

新增实现时建议：
1. 新建实现类并遵循接口签名。
2. 在 `ext/registry.py` 中注册并通过环境变量切换。
3. 增加合同测试覆盖核心行为。
Runnable HTTP examples are available in docs/requests.http (VS Code REST Client / JetBrains HTTP Client).
