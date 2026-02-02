from __future__ import annotations

import hashlib
import os
import uuid
from typing import Any, Optional

import httpx
import anyio

from .errors import PlasticMemoriesError, PlasticMemoriesTransportError, PlasticMemoriesProtocolError
from .models import Message, RecallResult, build_injection_block
from .retry import retry_call


def _is_async_transport(transport: httpx.BaseTransport | None) -> bool:
    return transport is not None and not hasattr(transport, "handle_request") and hasattr(transport, "handle_async_request")


def _stable_key(content: str) -> str:
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
    return f"msg_{digest}"


class PlasticMemoriesClient:
    def __init__(
        self,
        base_url: str,
        user_id: str = "local",
        persona_id: str = "default",
        source_app: str = "python_sdk",
        timeout_s: float = 10,
        default_headers: Optional[dict] = None,
        verify: bool | str | None = None,
        session_id: Optional[str] = None,
        api_key: Optional[str] = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.persona_id = persona_id
        self.source_app = source_app
        self.timeout_s = timeout_s
        self.api_key = api_key or os.getenv("PLASTIC_MEMORIES_API_KEY")
        self.default_headers = default_headers or {}
        if self.api_key and "X-API-Key" not in self.default_headers:
            self.default_headers["X-API-Key"] = self.api_key
        self.verify = verify
        self.session_id = session_id or self.new_session_id()
        self._async_transport = _is_async_transport(transport)
        if self._async_transport:
            self._client_async = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_s,
                headers=self.default_headers,
                verify=self.verify,
                transport=transport,
            )
            self._client = None
        else:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout_s,
                headers=self.default_headers,
                verify=self.verify,
                transport=transport,
            )
            self._client_async = None

    def close(self) -> None:
        if self._client:
            self._client.close()
        if self._client_async:
            anyio.run(self._client_async.aclose)

    @staticmethod
    def new_session_id() -> str:
        return uuid.uuid4().hex

    def _make_headers(self, headers: Optional[dict] = None) -> dict:
        merged = {}
        merged.update(self.default_headers)
        if headers:
            merged.update(headers)
        if self.api_key and "X-API-Key" not in merged:
            merged["X-API-Key"] = self.api_key
        if "X-Request-Id" not in merged:
            merged["X-Request-Id"] = uuid.uuid4().hex
        return merged

    def _parse_envelope(self, response: httpx.Response) -> tuple[dict, Optional[str]]:
        request_id = response.headers.get("X-Request-Id")
        try:
            payload = response.json()
        except Exception as exc:
            raise PlasticMemoriesProtocolError("响应不是有效 JSON", request_id=request_id) from exc
        if not isinstance(payload, dict) or "ok" not in payload:
            raise PlasticMemoriesProtocolError("响应不符合 Envelope 契约", request_id=request_id)
        if payload.get("ok") is True:
            if "data" not in payload:
                raise PlasticMemoriesProtocolError("响应缺少 data 字段", request_id=request_id)
            return payload["data"], request_id
        error = payload.get("error") or {}
        raise PlasticMemoriesError(
            code=error.get("code", "http_error"),
            message=error.get("message", "请求失败"),
            details=error.get("detail"),
            request_id=payload.get("request_id") or request_id,
            status_code=response.status_code,
        )

    async def _arequest(self, method: str, path: str, json_body: dict | None, params: dict | None, headers: dict | None) -> httpx.Response:
        assert self._client_async is not None
        return await self._client_async.request(
            method,
            path,
            json=json_body,
            params=params,
            headers=self._make_headers(headers),
        )

    def _request(self, method: str, path: str, *, json_body: dict | None = None, params: dict | None = None, headers: dict | None = None, retry: bool = False, disable_retry: bool = False) -> tuple[dict, Optional[str]]:
        def do_call():
            try:
                if self._async_transport:
                    resp = anyio.run(self._arequest, method, path, json_body, params, headers)
                else:
                    assert self._client is not None
                    resp = self._client.request(
                        method,
                        path,
                        json=json_body,
                        params=params,
                        headers=self._make_headers(headers),
                    )
            except Exception as exc:
                raise PlasticMemoriesTransportError(exc, request_id=None) from exc
            return resp

        try:
            if retry and not disable_retry:
                response = retry_call(do_call)
            else:
                response = do_call()
        except PlasticMemoriesTransportError:
            raise
        return self._parse_envelope(response)

    def health(self, disable_retry: bool = False) -> dict:
        data, _ = self._request("GET", "/health", retry=True, disable_retry=disable_retry)
        return data

    def capabilities(self, disable_retry: bool = False) -> dict:
        data, _ = self._request("GET", "/capabilities", retry=True, disable_retry=disable_retry)
        return data

    def persona_create(self, meta: dict | None = None, seed: dict | None = None) -> dict:
        payload = {"persona_id": self.persona_id}
        if meta:
            payload.update(meta)
        if seed:
            payload.update(seed)
        data, _ = self._request("POST", "/persona/create", json_body=payload)
        return data

    def create_from_template(self, template_path: str, allow_overwrite: bool = False) -> dict:
        payload = {
            "persona_id": self.persona_id,
            "template_path": template_path,
            "allow_overwrite": allow_overwrite,
        }
        data, _ = self._request("POST", "/persona/create_from_template", json_body=payload)
        return data

    def persona_profile(self, disable_retry: bool = False) -> dict:
        data, _ = self._request(
            "GET",
            "/persona/profile",
            params={"persona_id": self.persona_id},
            retry=True,
            disable_retry=disable_retry,
        )
        return data

    def recall(
        self,
        query: str,
        *,
        top_k: int | None = None,
        include_profile: bool = True,
        include_snippets: bool = True,
        snippets_days: int | None = None,
        top_k_snippets: int | None = None,
        filters: dict | None = None,
        disable_retry: bool = False,
    ) -> RecallResult:
        payload = {
            "persona_id": self.persona_id,
            "query": query,
            "limit": top_k or 10,
        }
        data, request_id = self._request("POST", "/memory/recall", json_body=payload, retry=True, disable_retry=disable_retry)
        persona_profile = data.get("PERSONA_PROFILE") if include_profile else None
        memory_items = data.get("PERSONA_MEMORY", []) if include_profile else []
        chat_snippets = data.get("CHAT_SNIPPETS", []) if include_snippets else []
        injection_block = build_injection_block(data)
        return RecallResult(
            raw=data,
            injection_block=injection_block,
            persona_profile=persona_profile,
            memory_items=memory_items,
            chat_snippets=chat_snippets,
            request_id=request_id,
        )

    def append_messages(self, messages: list[Message], *, session_id: str | None = None) -> dict:
        session = session_id or self.session_id
        message_ids = []
        for msg in messages:
            payload = {
                "persona_id": self.persona_id,
                "session_id": session,
                "source_app": self.source_app,
                "role": msg.role,
                "content": msg.content,
            }
            if msg.created_at:
                payload["ts"] = msg.created_at
            data, _ = self._request("POST", "/messages/append", json_body=payload)
            message_ids.append(data.get("message_id"))
        return {"message_ids": message_ids}

    def write(self, messages: list[Message], *, bypass_judge: bool = False, session_id: str | None = None) -> dict:
        written = 0
        for msg in messages:
            key = _stable_key(msg.content)
            payload = {
                "persona_id": self.persona_id,
                "type": "preferences",
                "key": key,
                "content": msg.content,
                "source_app": self.source_app,
            }
            self._request("POST", "/memory/write", json_body=payload)
            written += 1
        return {"written": written}

    def list_memory(self, type: str | None = None) -> dict:
        data, _ = self._request(
            "GET",
            "/memory/list",
            params={"persona_id": self.persona_id},
            retry=True,
        )
        items = data.get("items", [])
        if type:
            items = [item for item in items if item.get("type") == type]
        return {"items": items}

    def forget_memory(self, memory_id: str | None = None, match: dict | None = None) -> dict:
        if match is None:
            raise ValueError("forget_memory 需要 match 参数（含 type/key）")
        payload = {
            "persona_id": self.persona_id,
            "type": match.get("type"),
            "key": match.get("key"),
        }
        data, _ = self._request("POST", "/memory/forget", json_body=payload)
        return data

    def purge_messages(self, older_than_days: int) -> dict:
        payload = {
            "persona_id": self.persona_id,
            "days": older_than_days,
        }
        data, _ = self._request("POST", "/messages/purge", json_body=payload)
        return data
