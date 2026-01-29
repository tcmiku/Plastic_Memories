import json
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HttpResult:
    status: int
    headers: dict
    body_text: str


def http_json(method: str, url: str, payload: dict | None = None, headers: dict | None = None, timeout: float = 10.0) -> HttpResult:
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req_headers = {"Accept": "application/json"}
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url=url, data=data, method=method.upper(), headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return HttpResult(status=resp.status, headers=dict(resp.headers.items()), body_text=body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return HttpResult(status=e.code, headers=dict(e.headers.items()) if e.headers else {}, body_text=body)
    except Exception as e:
        return HttpResult(
            status=0,
            headers={},
            body_text=json.dumps(
                {"ok": False, "error": {"code": "transport_error", "message": str(e), "details": None}},
                ensure_ascii=False,
            ),
        )


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Plastic Memories API 验证工具（完整版：含记忆写入面板）")
        self.geometry("1280x820")
        self.minsize(1080, 700)

        # ====== 连接与身份 ======
        self.base_url = tk.StringVar(value="http://127.0.0.1:8007")
        self.user_id = tk.StringVar(value="local")
        self.persona_id = tk.StringVar(value="persona_1")
        self.source_app = tk.StringVar(value="pm_gui_验证工具")
        self.timeout_s = tk.DoubleVar(value=10.0)

        # ====== Endpoints ======
        self.ep_health = tk.StringVar(value="/health")
        self.ep_capabilities = tk.StringVar(value="/capabilities")
        self.ep_metrics = tk.StringVar(value="/metrics")
        self.ep_create_tpl = tk.StringVar(value="/persona/create_from_template")
        self.ep_recall = tk.StringVar(value="/memory/recall")
        self.ep_append = tk.StringVar(value="/messages/append")
        self.ep_recent = tk.StringVar(value="/messages/recent")
        self.ep_memory_write = tk.StringVar(value="/memory/write")   # 注意：这里是“单条记忆写入”接口
        self.ep_memory_list = tk.StringVar(value="/memory/list")

        # ====== 模板人格 ======
        self.template_path = tk.StringVar(value="personas/persona_1")
        self.allow_overwrite = tk.BooleanVar(value=False)

        # ====== Recall 参数 ======
        self.recall_query = tk.StringVar(value="我喜欢你怎么回答？")
        self.top_k = tk.IntVar(value=8)
        self.include_profile = tk.BooleanVar(value=True)
        self.include_snippets = tk.BooleanVar(value=True)
        self.snippets_days = tk.IntVar(value=30)
        self.top_k_snippets = tk.IntVar(value=5)

        # ====== 消息写入（snippets） ======
        self.demo_user_text_default = "以后回答尽量用步骤列表，代码优先给最小可运行版本。"

        # ====== 记忆写入面板（type/key/content） ======
        self.memory_types = ["persona", "preferences", "rule", "glossary", "stable_fact"]  # 从 /capabilities 也能获取
        self.mem_type = tk.StringVar(value="preferences")
        self.mem_key = tk.StringVar(value="response_style")
        self.mem_content = tk.StringVar(value=self.demo_user_text_default)

        self.last_request_id = None

        self._build_ui()

    # ================= UI =================
    def _build_ui(self):
        cfg = ttk.LabelFrame(self, text="连接与身份配置")
        cfg.pack(fill="x", padx=10, pady=8)

        ttk.Label(cfg, text="服务地址 Base URL").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(cfg, textvariable=self.base_url, width=48).grid(row=0, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(cfg, text="用户 ID").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(cfg, textvariable=self.user_id, width=16).grid(row=0, column=3, sticky="w", padx=6, pady=4)

        ttk.Label(cfg, text="人格 ID").grid(row=0, column=4, sticky="w", padx=6, pady=4)
        ttk.Entry(cfg, textvariable=self.persona_id, width=16).grid(row=0, column=5, sticky="w", padx=6, pady=4)

        ttk.Label(cfg, text="来源应用 source_app").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(cfg, textvariable=self.source_app, width=22).grid(row=1, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(cfg, text="请求超时（秒）").grid(row=1, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(cfg, textvariable=self.timeout_s, width=10).grid(row=1, column=3, sticky="w", padx=6, pady=4)

        ttk.Button(cfg, text="Endpoint 配置", command=self.open_endpoint_dialog).grid(row=1, column=5, sticky="e", padx=6, pady=4)
        cfg.grid_columnconfigure(1, weight=1)

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=8)

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=2)
        main.add(right, weight=3)

        # 左侧：操作区
        actions = ttk.LabelFrame(left, text="接口操作")
        actions.pack(fill="both", expand=True)

        # 基础
        basic = ttk.LabelFrame(actions, text="基础接口")
        basic.pack(fill="x", padx=8, pady=8)
        ttk.Button(basic, text="健康检查", command=self.call_health).pack(side="left", padx=6, pady=6)
        ttk.Button(basic, text="能力查询", command=self.call_capabilities).pack(side="left", padx=6, pady=6)
        ttk.Button(basic, text="运行指标", command=self.call_metrics).pack(side="left", padx=6, pady=6)

        # 模板人格
        tpl = ttk.LabelFrame(actions, text="人格模板注入（方式 C）")
        tpl.pack(fill="x", padx=8, pady=8)
        ttk.Label(tpl, text="模板路径").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(tpl, textvariable=self.template_path, width=42).grid(row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Checkbutton(tpl, text="允许覆盖", variable=self.allow_overwrite).grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Button(tpl, text="🚀 初始化 / 注入人格（从模板）", command=self.call_create_from_template).grid(
            row=1, column=0, columnspan=3, sticky="we", padx=6, pady=6
        )
        tpl.grid_columnconfigure(1, weight=1)

        # Recall
        rec = ttk.LabelFrame(actions, text="记忆召回（Recall）")
        rec.pack(fill="x", padx=8, pady=8)

        ttk.Label(rec, text="查询内容").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(rec, textvariable=self.recall_query, width=54).grid(row=0, column=1, columnspan=3, sticky="we", padx=6, pady=4)

        ttk.Label(rec, text="top_k").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(rec, textvariable=self.top_k, width=6).grid(row=1, column=1, sticky="w", padx=6, pady=4)
        ttk.Checkbutton(rec, text="包含人格 Profile", variable=self.include_profile).grid(row=1, column=2, sticky="w", padx=6, pady=4)
        ttk.Checkbutton(rec, text="包含聊天片段", variable=self.include_snippets).grid(row=1, column=3, sticky="w", padx=6, pady=4)

        row2 = ttk.Frame(rec)
        row2.grid(row=2, column=0, columnspan=4, sticky="we", padx=6, pady=(0, 4))
        ttk.Label(row2, text="snippets_days").pack(side="left")
        ttk.Entry(row2, textvariable=self.snippets_days, width=6).pack(side="left", padx=6)
        ttk.Label(row2, text="top_k_snippets").pack(side="left", padx=(12, 0))
        ttk.Entry(row2, textvariable=self.top_k_snippets, width=6).pack(side="left", padx=6)

        btn_line = ttk.Frame(rec)
        btn_line.grid(row=3, column=0, columnspan=4, sticky="we", padx=6, pady=6)
        ttk.Button(btn_line, text="执行 Recall", command=self.call_recall).pack(side="left")
        ttk.Button(btn_line, text="写入记忆后→自动 Recall", command=self.write_memory_then_recall).pack(side="left", padx=8)

        rec.grid_columnconfigure(1, weight=1)

        # 消息写入（snippets）
        msgbox = ttk.LabelFrame(actions, text="聊天原文（用于 CHAT_SNIPPETS）")
        msgbox.pack(fill="both", expand=True, padx=8, pady=8)

        ttk.Label(msgbox, text="示例用户消息（会作为 user role 写入）").pack(anchor="w", padx=6, pady=(6, 2))
        self.msg_text = tk.Text(msgbox, height=5, wrap="word")
        self.msg_text.pack(fill="x", padx=6, pady=4)
        self.msg_text.insert("1.0", self.demo_user_text_default)

        msgbtns = ttk.Frame(msgbox)
        msgbtns.pack(fill="x", padx=6, pady=6)
        ttk.Button(msgbtns, text="写入原始消息（append）", command=self.call_append_messages).pack(side="left", padx=6)
        ttk.Button(msgbtns, text="查看最近消息", command=self.call_messages_recent).pack(side="left", padx=6)

        # 记忆写入（type/key/content）——核心面板
        mempanel = ttk.LabelFrame(actions, text="长期记忆写入面板（type / key / content）")
        mempanel.pack(fill="x", padx=8, pady=8)

        ttk.Label(mempanel, text="type").grid(row=0, column=0, sticky="w", padx=6, pady=4)

        self.type_combo = ttk.Combobox(mempanel, textvariable=self.mem_type, values=self.memory_types, state="readonly", width=16)
        self.type_combo.grid(row=0, column=1, sticky="w", padx=6, pady=4)
        self.type_combo.bind("<<ComboboxSelected>>", self.on_type_change)

        ttk.Label(mempanel, text="key").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(mempanel, textvariable=self.mem_key, width=26).grid(row=0, column=3, sticky="we", padx=6, pady=4)

        ttk.Label(mempanel, text="content").grid(row=1, column=0, sticky="nw", padx=6, pady=4)
        self.mem_content_box = tk.Text(mempanel, height=5, wrap="word")
        self.mem_content_box.grid(row=1, column=1, columnspan=3, sticky="we", padx=6, pady=4)
        self.mem_content_box.insert("1.0", self.mem_content.get())

        sugg = ttk.Frame(mempanel)
        sugg.grid(row=2, column=0, columnspan=4, sticky="we", padx=6, pady=(0, 6))
        ttk.Label(sugg, text="快捷建议：").pack(side="left")
        ttk.Button(sugg, text="回答风格偏好", command=lambda: self.apply_suggestion("preferences", "response_style")).pack(side="left", padx=4)
        ttk.Button(sugg, text="用户称呼偏好", command=lambda: self.apply_suggestion("preferences", "user_name")).pack(side="left", padx=4)
        ttk.Button(sugg, text="术语表项", command=lambda: self.apply_suggestion("glossary", "term")).pack(side="left", padx=4)
        ttk.Button(sugg, text="稳定事实", command=lambda: self.apply_suggestion("stable_fact", "fact")).pack(side="left", padx=4)

        membtns = ttk.Frame(mempanel)
        membtns.grid(row=3, column=0, columnspan=4, sticky="we", padx=6, pady=6)
        ttk.Button(membtns, text="写入长期记忆（/memory/write）", command=self.call_memory_write_item).pack(side="left")
        ttk.Button(membtns, text="列出长期记忆（/memory/list）", command=self.call_memory_list).pack(side="left", padx=8)

        mempanel.grid_columnconfigure(3, weight=1)

        # 右侧：输出区（请求/响应）
        out = ttk.LabelFrame(right, text="请求 / 响应（含请求体）")
        out.pack(fill="both", expand=True)

        topbar = ttk.Frame(out)
        topbar.pack(fill="x", padx=8, pady=6)
        self.req_label = ttk.Label(topbar, text="尚未发送请求")
        self.req_label.pack(side="left")

        ttk.Button(topbar, text="复制响应", command=self.copy_response).pack(side="right", padx=6)
        ttk.Button(topbar, text="保存响应", command=self.save_response).pack(side="right", padx=6)
        ttk.Button(topbar, text="清空", command=self.clear_output).pack(side="right", padx=6)

        panes = ttk.PanedWindow(out, orient="vertical")
        panes.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        req_frame = ttk.LabelFrame(panes, text="实际请求（URL + JSON）")
        resp_frame = ttk.LabelFrame(panes, text="响应（JSON）")
        panes.add(req_frame, weight=1)
        panes.add(resp_frame, weight=2)

        self.req_text = tk.Text(req_frame, wrap="none", height=10)
        self.req_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.resp_text = tk.Text(resp_frame, wrap="none")
        self.resp_text.pack(fill="both", expand=True, padx=6, pady=6)

        self.status = ttk.Label(self, text="就绪", anchor="w")
        self.status.pack(fill="x", padx=10, pady=(0, 8))

    # ================= 交互逻辑 =================
    def set_status(self, s: str):
        self.status.config(text=s)

    def clear_output(self):
        self.req_text.delete("1.0", "end")
        self.resp_text.delete("1.0", "end")
        self.set_status("已清空")

    def copy_response(self):
        text = self.resp_text.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("已复制响应内容")

    def save_response(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json"), ("Text", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.resp_text.get("1.0", "end"))
        self.set_status(f"已保存到 {path}")

    def base(self) -> str:
        return self.base_url.get().rstrip("/")

    def ids(self) -> dict:
        return {"user_id": self.user_id.get().strip() or "local", "persona_id": self.persona_id.get().strip() or "default"}

    def make_session_id(self) -> str:
        return "gui-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    def _render_request_preview(self, preview: dict):
        self.req_text.delete("1.0", "end")
        self.req_text.insert("1.0", json.dumps(preview, ensure_ascii=False, indent=2))

    def render_result(self, method: str, path: str, payload: dict | None, res: HttpResult):
        rid = res.headers.get("X-Request-Id") or res.headers.get("x-request-id") or ""
        self.req_label.config(text=f"{method} {path} | 状态 {res.status} | request_id={rid}")

        body = res.body_text.strip()
        pretty = body
        try:
            obj = json.loads(body)
            pretty = json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            pass

        self.resp_text.delete("1.0", "end")
        self.resp_text.insert("1.0", pretty)
        self.set_status("请求完成")

        # 模板注入提示
        try:
            obj = json.loads(body)
            if obj.get("ok") is True and path == self.ep_create_tpl.get().strip():
                data = obj.get("data", {})
                if data.get("applied"):
                    messagebox.showinfo("人格注入成功", "人格已从模板成功注入（applied=true）。")
                elif data.get("skipped"):
                    messagebox.showinfo("人格已存在", "人格已存在，模板未覆盖（skipped=true，正常）。")
        except Exception:
            pass

    def run_call(self, method: str, path: str, payload: dict | None):
        def worker():
            base = self.base()
            url = base + path
            headers = {"X-Request-Id": self.last_request_id} if self.last_request_id else {}

            self.after(0, lambda: self._render_request_preview({"method": method, "url": url, "headers": headers, "json": payload}))
            self.set_status(f"请求中：{method} {path} ...")

            res = http_json(method, url, payload, headers=headers, timeout=float(self.timeout_s.get()))
            rid = res.headers.get("X-Request-Id") or res.headers.get("x-request-id")
            if rid:
                self.last_request_id = rid

            self.after(0, lambda: self.render_result(method, path, payload, res))

        threading.Thread(target=worker, daemon=True).start()

    # ================= Endpoint 配置 =================
    def open_endpoint_dialog(self):
        win = tk.Toplevel(self)
        win.title("Endpoint 配置")
        win.geometry("760x420")
        win.transient(self)

        ttk.Label(win, text="如果你的后端路由不是默认路径，可以在这里调整（一般保持默认即可）。").pack(anchor="w", padx=10, pady=(10, 6))

        frm = ttk.Frame(win)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        rows = [
            ("health", self.ep_health),
            ("capabilities", self.ep_capabilities),
            ("metrics", self.ep_metrics),
            ("persona.create_from_template", self.ep_create_tpl),
            ("memory.recall", self.ep_recall),
            ("messages.append", self.ep_append),
            ("messages.recent", self.ep_recent),
            ("memory.write（单条记忆写入）", self.ep_memory_write),
            ("memory.list", self.ep_memory_list),
        ]
        for i, (name, var) in enumerate(rows):
            ttk.Label(frm, text=name).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            ttk.Entry(frm, textvariable=var, width=56).grid(row=i, column=1, sticky="we", padx=6, pady=4)

        frm.grid_columnconfigure(1, weight=1)

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="关闭", command=win.destroy).pack(side="right")

    # ================= 业务按钮：基础/人格/召回 =================
    def call_health(self):
        self.run_call("GET", self.ep_health.get().strip(), None)

    def call_capabilities(self):
        self.run_call("GET", self.ep_capabilities.get().strip(), None)

    def call_metrics(self):
        self.run_call("GET", self.ep_metrics.get().strip(), None)

    def call_create_from_template(self):
        payload = {**self.ids(), "template_path": self.template_path.get().strip(), "allow_overwrite": bool(self.allow_overwrite.get())}
        self.run_call("POST", self.ep_create_tpl.get().strip(), payload)

    def call_recall(self):
        payload = {
            **self.ids(),
            "query": self.recall_query.get(),
            "top_k": int(self.top_k.get()),
            "include_profile": bool(self.include_profile.get()),
            "include_snippets": bool(self.include_snippets.get()),
            "snippets_days": int(self.snippets_days.get()),
            "top_k_snippets": int(self.top_k_snippets.get()),
        }
        self.run_call("POST", self.ep_recall.get().strip(), payload)

    # 写入记忆后自动 Recall（方便验证）
    def write_memory_then_recall(self):
        def after_write_render(res: HttpResult):
            # 写入成功后再 recall
            if res.status and 200 <= res.status < 300:
                self.call_recall()

        # 这里简单串行：写入后延时触发 recall
        self.call_memory_write_item(callback_after=after_write_render)

    # ================= 聊天原文（snippets） =================
    def build_demo_messages(self) -> list[dict]:
        user_text = self.msg_text.get("1.0", "end").strip()
        if not user_text:
            user_text = "你好"
        return [
            {"role": "user", "content": user_text, "created_at": iso_now()},
            {"role": "assistant", "content": "（这是用于 API 测试的示例 assistant 回复）", "created_at": iso_now()},
        ]

    # /messages/append：先批量，422 fallback 单条 role/content
    def call_append_messages(self):
        batch_payload = {
            **self.ids(),
            "source_app": self.source_app.get().strip() or "pm_gui_验证工具",
            "session_id": self.make_session_id(),
            "messages": self.build_demo_messages(),
        }
        path = self.ep_append.get().strip()

        def worker():
            base = self.base()
            url = base + path
            headers = {"X-Request-Id": self.last_request_id} if self.last_request_id else {}

            # 1) 批量
            self.after(0, lambda: self._render_request_preview({"method": "POST", "url": url, "headers": headers, "json": batch_payload}))
            res = http_json("POST", url, batch_payload, headers=headers, timeout=float(self.timeout_s.get()))
            rid = res.headers.get("X-Request-Id") or res.headers.get("x-request-id")
            if rid:
                self.last_request_id = rid

            if res.status and 200 <= res.status < 300:
                self.after(0, lambda: self.render_result("POST", path, batch_payload, res))
                return

            # 2) 422 -> 单条
            if res.status == 422:
                msgs = batch_payload.get("messages", [])
                last_res = res
                single_payload = None
                for m in msgs:
                    single_payload = {
                        **self.ids(),
                        "source_app": batch_payload["source_app"],
                        "session_id": batch_payload["session_id"],
                        "role": m.get("role"),
                        "content": m.get("content"),
                        "created_at": m.get("created_at"),
                    }
                    self.after(0, lambda sp=single_payload: self._render_request_preview({
                        "method": "POST", "url": url, "headers": headers, "json": sp, "note": "批量 422，自动 fallback 单条追加"
                    }))
                    last_res = http_json("POST", url, single_payload, headers=headers, timeout=float(self.timeout_s.get()))
                    rid2 = last_res.headers.get("X-Request-Id") or last_res.headers.get("x-request-id")
                    if rid2:
                        self.last_request_id = rid2
                    if not (last_res.status and 200 <= last_res.status < 300):
                        break

                self.after(0, lambda: self.render_result("POST", path, single_payload, last_res))
                return

            self.after(0, lambda: self.render_result("POST", path, batch_payload, res))

        threading.Thread(target=worker, daemon=True).start()

    def call_messages_recent(self):
        user_id = self.ids()["user_id"]
        persona_id = self.ids()["persona_id"]
        path = f"{self.ep_recent.get().strip()}?user_id={user_id}&persona_id={persona_id}&limit=20"
        self.run_call("GET", path, None)

    # ================= 长期记忆写入（type/key/content） =================
    def on_type_change(self, _evt=None):
        t = self.mem_type.get()
        # 根据 type 给一些 key 默认建议
        if t == "preferences":
            if not self.mem_key.get().strip() or self.mem_key.get().strip() in ("term", "fact"):
                self.mem_key.set("response_style")
        elif t == "glossary":
            self.mem_key.set("term")
        elif t == "stable_fact":
            self.mem_key.set("fact")
        elif t == "rule":
            self.mem_key.set("behavior_rule")
        elif t == "persona":
            self.mem_key.set("persona_md")

    def apply_suggestion(self, typ: str, key: str):
        self.mem_type.set(typ)
        self.mem_key.set(key)
        # 默认把消息框文本作为 content 起点
        txt = self.msg_text.get("1.0", "end").strip() or self.demo_user_text_default
        self.mem_content_box.delete("1.0", "end")
        self.mem_content_box.insert("1.0", txt)

    def call_memory_write_item(self, callback_after=None):
        # 从 text box 取 content
        content = self.mem_content_box.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("缺少内容", "content 不能为空。")
            return

        typ = self.mem_type.get().strip()
        key = self.mem_key.get().strip()

        if typ not in self.memory_types:
            messagebox.showwarning("type 不合法", f"type 必须是 {self.memory_types} 之一")
            return
        if not key:
            messagebox.showwarning("缺少 key", "key 不能为空。")
            return

        payload = {
            **self.ids(),
            "type": typ,
            "key": key,
            "content": content,
        }

        path = self.ep_memory_write.get().strip()

        def worker():
            base = self.base()
            url = base + path
            headers = {"X-Request-Id": self.last_request_id} if self.last_request_id else {}

            self.after(0, lambda: self._render_request_preview({"method": "POST", "url": url, "headers": headers, "json": payload}))
            self.set_status(f"请求中：POST {path} ...")

            res = http_json("POST", url, payload, headers=headers, timeout=float(self.timeout_s.get()))
            rid = res.headers.get("X-Request-Id") or res.headers.get("x-request-id")
            if rid:
                self.last_request_id = rid

            self.after(0, lambda: self.render_result("POST", path, payload, res))

            # 写入成功后可自动刷新 list
            if res.status and 200 <= res.status < 300:
                self.after(150, self.call_memory_list)
            if callback_after:
                try:
                    callback_after(res)
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def call_memory_list(self):
        user_id = self.ids()["user_id"]
        persona_id = self.ids()["persona_id"]
        path = f"{self.ep_memory_list.get().strip()}?user_id={user_id}&persona_id={persona_id}"
        self.run_call("GET", path, None)


if __name__ == "__main__":
    try:
        import tkinter  # noqa
    except Exception:
        raise SystemExit("当前 Python 未安装 Tkinter。Linux 可执行：sudo apt install python3-tk")

    App().mainloop()
