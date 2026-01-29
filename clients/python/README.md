# Plastic Memories Python SDK

官方 Python SDK，用于任何外部程序（tools_live2D/CLI/IDE/Web）统一接入 Plastic Memories。

## 安装方式（仓库内使用）

在仓库根目录直接导入：

```bash
python -c "from clients.python.plastic_memories_client import PlasticMemoriesClient; print(PlasticMemoriesClient)"
```

如需在其它项目中引用，可将 `clients/python` 加入 `PYTHONPATH`。

## 最小示例（召回注入 + 追加 + 写入）

```python
from clients.python.plastic_memories_client import PlasticMemoriesClient, Message

client = PlasticMemoriesClient(base_url="http://127.0.0.1:8007", user_id="local", persona_id="default")

# 召回注入
recall = client.recall("请总结我喜欢的回答风格")
print(recall.injection_block)

# 追加消息
client.append_messages([
    Message(role="user", content="请用默认中文"),
    Message(role="user", content="回答工程化"),
])

# 写入记忆
client.write([
    Message(role="user", content="叫我 tcmiku"),
])
```

从模板创建人格示例：

```python
client.create_from_template("personas/persona_1", allow_overwrite=False)
```

## 与 tools_live2D 接入建议

推荐流程：
1) 聊天前先 `recall()`，将 `injection_block` 注入系统提示。
2) 聊天后将对话追加：`append_messages()`。
3) 对需要长期保存的偏好再 `write()`。

## 契约测试说明

SDK 契约测试使用 ASGITransport 直接打后端应用，不需要启动 uvicorn：

```bash
pytest -q tests/client_contract
```
