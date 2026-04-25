"""REST：自动回复规则 + 异步任务（JWT）。"""

from __future__ import annotations

import logging
import threading
from typing import Any
import multiprocessing as mp

from django.conf import settings
from django.http import HttpRequest
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from ai_engine.auth import JWTAuth
from ai_engine.models import (
    AutoReplyChatHistoryEntry,
    AutoReplyJob,
    AutoReplyKnowledgeEntry,
    AutoReplyRule,
    AutoReplyScreenProfile,
)

logger = logging.getLogger(__name__)

auto_reply_router = Router(tags=["AI Auto Reply"], auth=JWTAuth())

class _AgentHandle:
    def __init__(self, *, kind: str, proc: mp.Process | None = None, thread: threading.Thread | None = None, stop=None):
        self.kind = kind
        self.proc = proc
        self.thread = thread
        self.stop = stop


# 本机屏幕代理（每用户一个）。
# - 优先 multiprocessing 子进程（隔离依赖/崩溃）
# - Windows/开发环境下若启动失败，回退到线程（避免 500 直接不可用）
_agent_handle_by_user: dict[int, _AgentHandle] = {}


def _proc_is_alive(p: mp.Process | None) -> bool:
    try:
        return bool(p is not None and p.is_alive())
    except Exception:
        return False


def _agent_is_running(h: _AgentHandle | None) -> bool:
    if h is None:
        return False
    if h.kind == "process":
        return _proc_is_alive(h.proc)
    if h.kind == "thread":
        try:
            return bool(h.thread is not None and h.thread.is_alive())
        except Exception:
            return False
    return False


@auto_reply_router.get("/agent/status")
def agent_status(request: HttpRequest):
    from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    h = _agent_handle_by_user.get(int(u.pk))
    pid = getattr(h.proc, "pid", None) if h and h.kind == "process" else None
    return {"running": _agent_is_running(h), "pid": pid}


@auto_reply_router.post("/agent/start")
def agent_start(request: HttpRequest):
    from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")

    uid = int(u.pk)
    existing = _agent_handle_by_user.get(uid)
    if _agent_is_running(existing):
        return {"ok": True, "running": True, "pid": getattr(existing.proc, "pid", None)}

    from ai_engine.desktop_screen_agent.server_runner import run_server_screen_agent

    ctx = mp.get_context("spawn")

    stop_evt = ctx.Event()

    def _entry(user_id: int, stop_event) -> None:
        import os
        import django

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flowly_backend.settings")
        django.setup()
        run_server_screen_agent(user_id=int(user_id), stop_event=stop_event)

    try:
        p = ctx.Process(target=_entry, args=(uid, stop_evt), name=f"flowly-screen-agent-{uid}")
        p.daemon = True
        p.start()
        _agent_handle_by_user[uid] = _AgentHandle(kind="process", proc=p, stop=stop_evt)
        return {"ok": True, "running": True, "pid": p.pid}
    except Exception as exc:
        # 回退到线程模式（无法返回子进程 pid）
        try:
            stop_evt2 = threading.Event()

            def _t_entry():
                import os
                import django

                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flowly_backend.settings")
                django.setup()
                run_server_screen_agent(user_id=uid, stop_event=stop_evt2)

            t = threading.Thread(target=_t_entry, daemon=True, name=f"flowly-screen-agent-thread-{uid}")
            t.start()
            _agent_handle_by_user[uid] = _AgentHandle(kind="thread", thread=t, stop=stop_evt2)
            return {"ok": True, "running": True, "pid": None}
        except Exception as exc2:
            raise HttpError(500, f"启动失败: {exc}; 线程回退也失败: {exc2}") from exc2


@auto_reply_router.post("/agent/stop")
def agent_stop(request: HttpRequest):
    from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    uid = int(u.pk)
    h = _agent_handle_by_user.get(uid)
    if not _agent_is_running(h):
        _agent_handle_by_user.pop(uid, None)
        return {"ok": True, "running": False}
    try:
        if h and h.stop is not None and getattr(h.stop, "set", None):
            h.stop.set()
    except Exception:
        pass
    try:
        if h and h.kind == "process" and h.proc is not None:
            h.proc.terminate()
    except Exception:
        pass
    _agent_handle_by_user.pop(uid, None)
    return {"ok": True, "running": False}


@auto_reply_router.get("/presets")
def auto_reply_presets(request: HttpRequest):
    """人格 / 情景预设列表（与参考桌面端键一致，数据存库时存 key）。"""
    if request.auth is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    from ai_engine.auto_reply.presets import CHAT_PERSONALITIES, CHAT_PERSONALITY_LABELS, CHAT_SCENES

    scenes = [{"key": k, "label": v} for k, v in CHAT_SCENES.items()]
    personalities = [
        {"key": k, "label": CHAT_PERSONALITY_LABELS.get(k, k), "hint": v}
        for k, v in CHAT_PERSONALITIES.items()
    ]
    return {"scenes": scenes, "personalities": personalities}


class AutoReplyRuleOut(Schema):
    id: int
    name: str
    system_prompt: str
    personality_key: str = ""
    scene_key: str = ""
    model_key: str
    is_active: bool
    updated_at: str


class AutoReplyRuleCreate(Schema):
    name: str = Field(..., min_length=1, max_length=128)
    system_prompt: str = Field(default="", max_length=50000)
    personality_key: str = Field(default="", max_length=64)
    scene_key: str = Field(default="", max_length=64)
    model_key: str = Field(default="", max_length=96)
    is_active: bool = True


class AutoReplyRulePatch(Schema):
    name: str | None = Field(default=None, max_length=128)
    system_prompt: str | None = None
    personality_key: str | None = Field(default=None, max_length=64)
    scene_key: str | None = Field(default=None, max_length=64)
    model_key: str | None = Field(default=None, max_length=96)
    is_active: bool | None = None


class AutoReplyJobOut(Schema):
    id: int
    status: str
    input_text: str
    friend_name: str = ""
    reply_text: str
    error_message: str
    model_key_used: str
    rule_id: int | None
    created_at: str
    updated_at: str


class AutoReplyJobCreate(Schema):
    message: str = Field(..., min_length=1, max_length=16000)
    rule_id: int | None = None
    friend_name: str = Field(default="", max_length=128)


def _norm_box4(name: str, v: Any) -> list[int] | None:
    if v is None:
        return None
    if isinstance(v, (list, tuple)) and len(v) == 4:
        try:
            return [int(x) for x in v]
        except Exception as e:
            raise ValueError(f"{name} 须为 4 个整数") from e
    raise ValueError(f"{name} 须为长度 4 的列表")


class AutoReplyScreenProfileOut(Schema):
    chat_software: str
    chat_window_box: list[int] | None = None
    input_box_pos: list[int] | None = None
    user_name_box: list[int] | None = None
    friend_list_box: list[int] | None = None
    monitored_friends: list[str] = Field(default_factory=list)
    friends_overrides: dict[str, Any] = Field(default_factory=dict)
    check_interval_seconds: int = 3
    use_yolo: bool = True
    knowledge_reply_enabled: bool = False
    monitoring_active: bool = False
    yolo_weights_path: str = ""
    region_detect_nonce: int = 0
    region_detect_ack_nonce: int = 0
    default_rule_id: int | None = None
    updated_at: str = ""
    agent_runtime_snapshot: dict[str, Any] = Field(default_factory=dict)


class AutoReplyScreenProfileWrite(Schema):
    chat_software: str = Field(default="wechat", max_length=32)
    chat_window_box: list[int] | None = None
    input_box_pos: list[int] | None = None
    user_name_box: list[int] | None = None
    friend_list_box: list[int] | None = None
    monitored_friends: list[str] = Field(default_factory=list)
    friends_overrides: dict[str, Any] = Field(default_factory=dict)
    check_interval_seconds: int = Field(default=3, ge=1, le=600)
    use_yolo: bool = True
    knowledge_reply_enabled: bool = False
    monitoring_active: bool = False
    yolo_weights_path: str = Field(default="", max_length=512)
    default_rule_id: int | None = None


class ScreenLayoutPatch(Schema):
    """本机代理写回识别框；可选附带 region_detect_ack_nonce 与当前 region_detect_nonce 对齐。"""

    chat_window_box: list[int] | None = None
    input_box_pos: list[int] | None = None
    user_name_box: list[int] | None = None
    friend_list_box: list[int] | None = None
    region_detect_ack_nonce: int | None = None


class AutoReplyKnowledgeOut(Schema):
    id: int
    scope: str
    friend_name: str
    title: str
    body: str
    trigger_keywords: list[str] = Field(default_factory=list)
    is_active: bool
    sort_order: int
    updated_at: str


class AutoReplyKnowledgeWrite(Schema):
    scope: str = Field(default="shared", max_length=16)
    friend_name: str = Field(default="", max_length=128)
    title: str = Field(default="", max_length=256)
    body: str = Field(..., min_length=1, max_length=200000)
    trigger_keywords: list[str] = Field(default_factory=list)
    is_active: bool = True
    sort_order: int = 0


class AutoReplyKnowledgePatch(Schema):
    scope: str | None = Field(default=None, max_length=16)
    friend_name: str | None = Field(default=None, max_length=128)
    title: str | None = Field(default=None, max_length=256)
    body: str | None = Field(default=None, max_length=200000)
    trigger_keywords: list[str] | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class AutoReplyChatHistoryOut(Schema):
    id: int
    friend_name: str
    role: str
    content: str
    meta: dict[str, Any]
    created_at: str


class AutoReplyChatHistoryCreate(Schema):
    friend_name: str = Field(default="", max_length=128)
    role: str = Field(default="user", max_length=16)
    content: str = Field(..., min_length=1, max_length=32000)
    meta: dict[str, Any] = Field(default_factory=dict)


#
# 说明：
#   AutoReplyScreenEvent / AutoReplyMonitorLogLine 已按需求下线：
#   - 不再将屏幕代理事件/日志写入数据库
#   - 相关 API（/screen-events, /monitor-logs）同步移除


def _rule_out(r: AutoReplyRule) -> dict[str, Any]:
    return {
        "id": r.pk,
        "name": r.name,
        "system_prompt": r.system_prompt or "",
        "personality_key": getattr(r, "personality_key", "") or "",
        "scene_key": getattr(r, "scene_key", "") or "",
        "model_key": r.model_key or "",
        "is_active": r.is_active,
        "updated_at": r.updated_at.isoformat() if r.updated_at else "",
    }


def _job_out(j: AutoReplyJob) -> dict[str, Any]:
    return {
        "id": j.pk,
        "status": j.status,
        "input_text": j.input_text,
        "friend_name": getattr(j, "friend_name", "") or "",
        "reply_text": j.reply_text or "",
        "error_message": j.error_message or "",
        "model_key_used": j.model_key_used or "",
        "rule_id": j.rule_id,
        "created_at": j.created_at.isoformat() if j.created_at else "",
        "updated_at": j.updated_at.isoformat() if j.updated_at else "",
    }


def _screen_profile_out(p: AutoReplyScreenProfile) -> dict[str, Any]:
    mf = p.monitored_friends if isinstance(p.monitored_friends, list) else []
    fo = p.friends_overrides if isinstance(p.friends_overrides, dict) else {}
    return {
        "chat_software": p.chat_software or "wechat",
        "chat_window_box": p.chat_window_box,
        "input_box_pos": p.input_box_pos,
        "user_name_box": p.user_name_box,
        "friend_list_box": p.friend_list_box,
        "monitored_friends": [str(x) for x in mf],
        "friends_overrides": fo,
        "check_interval_seconds": int(p.check_interval_seconds or 3),
        "use_yolo": bool(p.use_yolo),
        "knowledge_reply_enabled": bool(p.knowledge_reply_enabled),
        "monitoring_active": bool(getattr(p, "monitoring_active", False)),
        "yolo_weights_path": getattr(p, "yolo_weights_path", "") or "",
        "region_detect_nonce": int(getattr(p, "region_detect_nonce", 0) or 0),
        "region_detect_ack_nonce": int(getattr(p, "region_detect_ack_nonce", 0) or 0),
        "default_rule_id": p.default_rule_id,
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
        "agent_runtime_snapshot": getattr(p, "agent_runtime_snapshot", None)
        if isinstance(getattr(p, "agent_runtime_snapshot", None), dict)
        else {},
    }


@auto_reply_router.get("/screen-profile", response=AutoReplyScreenProfileOut)
def get_screen_profile(request: HttpRequest):
    from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    p, _ = AutoReplyScreenProfile.objects.get_or_create(user=u)
    return _screen_profile_out(p)


@auto_reply_router.put("/screen-profile", response=AutoReplyScreenProfileOut)
def put_screen_profile(request: HttpRequest, payload: AutoReplyScreenProfileWrite):
    from ninja.errors import AuthenticationError, HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    try:
        cw = _norm_box4("chat_window_box", payload.chat_window_box)
        ip = _norm_box4("input_box_pos", payload.input_box_pos)
        un = _norm_box4("user_name_box", payload.user_name_box)
        fl = _norm_box4("friend_list_box", payload.friend_list_box)
    except ValueError as ve:
        raise HttpError(400, str(ve)) from ve
    rule = None
    if payload.default_rule_id is not None:
        rule = AutoReplyRule.objects.filter(pk=payload.default_rule_id, user=u).first()
        if rule is None:
            raise HttpError(400, "default_rule_id 不存在或不属于当前用户")
    p, _ = AutoReplyScreenProfile.objects.get_or_create(user=u)
    p.chat_software = (payload.chat_software or "wechat").strip() or "wechat"
    p.chat_window_box = cw
    p.input_box_pos = ip
    p.user_name_box = un
    p.friend_list_box = fl
    p.monitored_friends = list(payload.monitored_friends or [])
    p.friends_overrides = dict(payload.friends_overrides or {})
    p.check_interval_seconds = int(payload.check_interval_seconds)
    p.use_yolo = bool(payload.use_yolo)
    p.knowledge_reply_enabled = bool(payload.knowledge_reply_enabled)
    p.monitoring_active = bool(payload.monitoring_active)
    # 项目约定：仅使用仓库根目录 best.pt（或环境变量 FLOWLY_SCREEN_YOLO_WEIGHTS 覆盖）
    # 前端仍保留字段显示，但保存时由服务端统一落为 settings.FLOWLY_SCREEN_YOLO_WEIGHTS
    p.yolo_weights_path = str(getattr(settings, "FLOWLY_SCREEN_YOLO_WEIGHTS", "") or "").strip()[:512]
    p.default_rule = rule
    p.save()
    p.refresh_from_db()
    return _screen_profile_out(p)


@auto_reply_router.patch("/screen-profile/layout", response=AutoReplyScreenProfileOut)
def patch_screen_layout(request: HttpRequest, payload: ScreenLayoutPatch):
    from ninja.errors import AuthenticationError, HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    p, _ = AutoReplyScreenProfile.objects.get_or_create(user=u)
    data = payload.model_dump(exclude_unset=True)
    ack = data.pop("region_detect_ack_nonce", None)
    if ack is not None:
        if int(ack) != int(p.region_detect_nonce or 0):
            raise HttpError(400, "region_detect_ack_nonce 与当前 region_detect_nonce 不一致")
        p.region_detect_ack_nonce = int(ack)
    for key in ("chat_window_box", "input_box_pos", "user_name_box", "friend_list_box"):
        if key not in data:
            continue
        val = data[key]
        if val is None:
            setattr(p, key, None)
            continue
        try:
            setattr(p, key, _norm_box4(key, val))
        except ValueError as ve:
            raise HttpError(400, str(ve)) from ve
    p.save()
    p.refresh_from_db()
    return _screen_profile_out(p)


@auto_reply_router.post("/screen-profile/request-region-detect", response=AutoReplyScreenProfileOut)
def request_region_detect(request: HttpRequest):
    from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    p, _ = AutoReplyScreenProfile.objects.get_or_create(user=u)
    p.region_detect_nonce = int(p.region_detect_nonce or 0) + 1
    p.save(update_fields=["region_detect_nonce", "updated_at"])
    p.refresh_from_db()
    return _screen_profile_out(p)


def _knowledge_out(e: AutoReplyKnowledgeEntry) -> dict[str, Any]:
    kws = e.trigger_keywords if isinstance(e.trigger_keywords, list) else []
    return {
        "id": e.pk,
        "scope": e.scope,
        "friend_name": e.friend_name or "",
        "title": e.title or "",
        "body": e.body or "",
        "trigger_keywords": [str(x) for x in kws],
        "is_active": e.is_active,
        "sort_order": int(e.sort_order or 0),
        "updated_at": e.updated_at.isoformat() if e.updated_at else "",
    }


def _chat_hist_out(row: AutoReplyChatHistoryEntry) -> dict[str, Any]:
    return {
        "id": row.pk,
        "friend_name": row.friend_name or "",
        "role": row.role,
        "content": row.content,
        "meta": row.meta if isinstance(row.meta, dict) else {},
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


@auto_reply_router.get("/knowledge-entries", response=list[AutoReplyKnowledgeOut])
def list_knowledge_entries(request: HttpRequest):
    from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    rows = AutoReplyKnowledgeEntry.objects.filter(user=u).order_by("sort_order", "id")[:500]
    return [_knowledge_out(r) for r in rows]


@auto_reply_router.post("/knowledge-entries", response={201: AutoReplyKnowledgeOut})
def create_knowledge_entry(request: HttpRequest, payload: AutoReplyKnowledgeWrite):
    from ninja.errors import AuthenticationError, HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    sc = (payload.scope or "shared").strip()
    if sc not in (AutoReplyKnowledgeEntry.Scope.SHARED, AutoReplyKnowledgeEntry.Scope.FRIEND):
        raise HttpError(400, "scope 须为 shared 或 friend")
    fn = (payload.friend_name or "").strip()[:128]
    if sc == AutoReplyKnowledgeEntry.Scope.FRIEND and not fn:
        raise HttpError(400, "friend 范围须填写 friend_name")
    kws = [str(x).strip() for x in (payload.trigger_keywords or []) if str(x).strip()]
    e = AutoReplyKnowledgeEntry.objects.create(
        user=u,
        scope=sc,
        friend_name=fn,
        title=(payload.title or "").strip()[:256],
        body=payload.body.strip(),
        trigger_keywords=kws,
        is_active=bool(payload.is_active),
        sort_order=int(payload.sort_order or 0),
    )
    return 201, _knowledge_out(e)


@auto_reply_router.patch("/knowledge-entries/{entry_id}", response=AutoReplyKnowledgeOut)
def patch_knowledge_entry(request: HttpRequest, entry_id: int, payload: AutoReplyKnowledgePatch):
    from ninja.errors import AuthenticationError, HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    e = AutoReplyKnowledgeEntry.objects.filter(pk=entry_id, user=u).first()
    if e is None:
        raise HttpError(404, "条目不存在")
    data = payload.model_dump(exclude_unset=True)
    if "scope" in data and data["scope"] is not None:
        sc = str(data["scope"]).strip()
        if sc not in (AutoReplyKnowledgeEntry.Scope.SHARED, AutoReplyKnowledgeEntry.Scope.FRIEND):
            raise HttpError(400, "scope 无效")
        e.scope = sc
    if "friend_name" in data and data["friend_name"] is not None:
        e.friend_name = str(data["friend_name"]).strip()[:128]
    if "title" in data and data["title"] is not None:
        e.title = str(data["title"]).strip()[:256]
    if "body" in data and data["body"] is not None:
        e.body = str(data["body"]).strip()
    if "trigger_keywords" in data and data["trigger_keywords"] is not None:
        e.trigger_keywords = [str(x).strip() for x in data["trigger_keywords"] if str(x).strip()]
    if "is_active" in data and data["is_active"] is not None:
        e.is_active = bool(data["is_active"])
    if "sort_order" in data and data["sort_order"] is not None:
        e.sort_order = int(data["sort_order"])
    if e.scope == AutoReplyKnowledgeEntry.Scope.FRIEND and not (e.friend_name or "").strip():
        raise HttpError(400, "friend 范围须填写 friend_name")
    e.save()
    e.refresh_from_db()
    return _knowledge_out(e)


@auto_reply_router.delete("/knowledge-entries/{entry_id}", response={200: dict})
def delete_knowledge_entry(request: HttpRequest, entry_id: int):
    from ninja.errors import AuthenticationError, HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    n, _ = AutoReplyKnowledgeEntry.objects.filter(pk=entry_id, user=u).delete()
    if not n:
        raise HttpError(404, "条目不存在")
    return 200, {"ok": True}


@auto_reply_router.get("/chat-history", response=list[AutoReplyChatHistoryOut])
def list_chat_history(request: HttpRequest, friend: str = "", limit: int = 80):
    from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    lim = max(1, min(limit, 300))
    qs = AutoReplyChatHistoryEntry.objects.filter(user=u)
    fn = (friend or "").strip()
    if fn:
        qs = qs.filter(friend_name=fn)
    rows = qs.order_by("-created_at")[:lim]
    return [_chat_hist_out(r) for r in rows]


@auto_reply_router.post("/chat-history", response={201: AutoReplyChatHistoryOut})
def create_chat_history(request: HttpRequest, payload: AutoReplyChatHistoryCreate):
    from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        raise AuthenticationError("Authentication required")
    role = (payload.role or "user").strip()[:16]
    if role not in {x[0] for x in AutoReplyChatHistoryEntry.Role.choices}:
        role = AutoReplyChatHistoryEntry.Role.USER
    row = AutoReplyChatHistoryEntry.objects.create(
        user=u,
        friend_name=(payload.friend_name or "").strip()[:128],
        role=role,
        content=payload.content.strip(),
        meta=dict(payload.meta or {}),
    )
    return 201, _chat_hist_out(row)


@auto_reply_router.get("/rules", response=list[AutoReplyRuleOut])
def list_rules(request: HttpRequest):
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    rows = AutoReplyRule.objects.filter(user=u).order_by("-updated_at")[:200]
    return [_rule_out(r) for r in rows]


@auto_reply_router.post("/rules", response={201: AutoReplyRuleOut})
def create_rule(request: HttpRequest, payload: AutoReplyRuleCreate):
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    sp = (payload.system_prompt or "").strip()
    pk = (payload.personality_key or "").strip()
    sk = (payload.scene_key or "").strip()
    if not sp and not pk and not sk:
        raise HttpError(400, "请填写自定义系统提示，或至少选择人格 / 情景预设之一")
    r = AutoReplyRule.objects.create(
        user=u,
        name=payload.name.strip(),
        system_prompt=sp,
        personality_key=pk,
        scene_key=sk,
        model_key=(payload.model_key or "").strip(),
        is_active=payload.is_active,
    )
    return 201, _rule_out(r)


@auto_reply_router.patch("/rules/{rule_id}", response=AutoReplyRuleOut)
def patch_rule(request: HttpRequest, rule_id: int, payload: AutoReplyRulePatch):
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    r = AutoReplyRule.objects.filter(pk=rule_id, user=u).first()
    if r is None:
        raise HttpError(404, "规则不存在")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        r.name = str(data["name"]).strip()
    if "system_prompt" in data and data["system_prompt"] is not None:
        r.system_prompt = str(data["system_prompt"]).strip()
    if "personality_key" in data and data["personality_key"] is not None:
        r.personality_key = str(data["personality_key"]).strip()
    if "scene_key" in data and data["scene_key"] is not None:
        r.scene_key = str(data["scene_key"]).strip()
    if "model_key" in data and data["model_key"] is not None:
        r.model_key = str(data["model_key"]).strip()
    if "is_active" in data and data["is_active"] is not None:
        r.is_active = bool(data["is_active"])
    r.save()
    return _rule_out(r)


@auto_reply_router.delete("/rules/{rule_id}", response={200: dict})
def delete_rule(request: HttpRequest, rule_id: int):
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    n, _ = AutoReplyRule.objects.filter(pk=rule_id, user=u).delete()
    if not n:
        raise HttpError(404, "规则不存在")
    return 200, {"ok": True}


@auto_reply_router.get("/jobs", response=list[AutoReplyJobOut])
def list_jobs(request: HttpRequest, limit: int = 50):
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    lim = max(1, min(limit, 200))
    rows = AutoReplyJob.objects.filter(user=u).order_by("-created_at")[:lim]
    return [_job_out(j) for j in rows]


@auto_reply_router.get("/jobs/{job_id}", response=AutoReplyJobOut)
def get_job(request: HttpRequest, job_id: int):
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    j = AutoReplyJob.objects.filter(pk=job_id, user=u).first()
    if j is None:
        raise HttpError(404, "任务不存在")
    return _job_out(j)


def _enqueue_job(job_id: int) -> None:
    use_sub = str(getattr(settings, "FLOWLY_AUTO_REPLY_USE_SUBPROCESS", "") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    if use_sub:
        from ai_engine.auto_reply.runner import run_auto_reply_job_in_subprocess

        run_auto_reply_job_in_subprocess(job_id)
        return
    try:
        from ai_engine.tasks import run_auto_reply_job_task

        run_auto_reply_job_task.delay(job_id)
    except Exception:
        logger.warning("Celery enqueue failed for auto_reply job %s; falling back to thread", job_id, exc_info=True)
        from ai_engine.auto_reply.runner import run_auto_reply_job_sync

        threading.Thread(target=lambda: run_auto_reply_job_sync(job_id), daemon=True).start()


@auto_reply_router.post("/jobs", response={201: AutoReplyJobOut})
def create_job(request: HttpRequest, payload: AutoReplyJobCreate):
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    rule = None
    if payload.rule_id is not None:
        rule = AutoReplyRule.objects.filter(pk=payload.rule_id, user=u, is_active=True).first()
        if rule is None:
            raise HttpError(400, "规则不存在或未启用")
    job = AutoReplyJob.objects.create(
        user=u,
        rule=rule,
        input_text=payload.message.strip(),
        friend_name=(payload.friend_name or "").strip()[:128],
        status=AutoReplyJob.Status.PENDING,
    )
    _enqueue_job(job.pk)
    job.refresh_from_db()
    return 201, _job_out(job)
