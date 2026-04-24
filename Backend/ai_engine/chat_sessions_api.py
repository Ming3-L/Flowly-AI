"""独立 AI 对话会话：列表 / 新建 / 删除 / 消息 / 清空（JWT）。"""

from __future__ import annotations

from typing import Any

from django.db.models import Count
from django.http import HttpRequest
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from ai_engine.auth import JWTAuth
from ai_engine.conversation import persist as chat_persist
from ai_engine.models import ConversationMessage, ConversationSession

chat_sessions_router = Router(tags=["Chat Sessions"], auth=JWTAuth())


class ChatSessionListItemSchema(Schema):
    id: int
    topic: str
    updated_at: str
    message_count: int


class ChatSessionListSchema(Schema):
    sessions: list[ChatSessionListItemSchema]


class ChatSessionCreateSchema(Schema):
    topic: str = Field(default="", max_length=255)


class ChatSessionCreateOutSchema(Schema):
    id: int
    topic: str


class ChatMessageOutSchema(Schema):
    id: int
    role: str
    content: str
    created_at: str


class ChatMessagesOutSchema(Schema):
    messages: list[ChatMessageOutSchema]


@chat_sessions_router.get("/sessions", response=ChatSessionListSchema)
def list_chat_sessions(request: HttpRequest):
    """GET /api/chat/sessions — 当前用户最多 50 条，按更新时间倒序。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    qs = (
        ConversationSession.objects.filter(user=u)
        .annotate(message_count=Count("messages"))
        .order_by("-updated_at")[: chat_persist.MAX_SESSIONS_PER_USER]
    )
    out: list[dict[str, Any]] = []
    for s in qs:
        out.append(
            {
                "id": s.pk,
                "topic": s.topic or "",
                "updated_at": s.updated_at.isoformat() if s.updated_at else "",
                "message_count": int(getattr(s, "message_count", 0) or 0),
            }
        )
    return ChatSessionListSchema(sessions=[ChatSessionListItemSchema(**x) for x in out])


@chat_sessions_router.post("/sessions", response={201: ChatSessionCreateOutSchema})
def create_chat_session(request: HttpRequest, payload: ChatSessionCreateSchema):
    """POST /api/chat/sessions — 新建会话（超出 50 条时自动删最旧）。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    s = chat_persist.create_session(user=u, topic=(payload.topic or "").strip())
    return 201, ChatSessionCreateOutSchema(id=s.pk, topic=s.topic or "")


@chat_sessions_router.delete("/sessions/{session_id}", response={200: dict})
def delete_chat_session(request: HttpRequest, session_id: int):
    """DELETE /api/chat/sessions/{id} — 删除整个会话。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    n, _ = ConversationSession.objects.filter(pk=session_id, user=u).delete()
    if not n:
        from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

        raise HttpError(404, "会话不存在")
    return 200, {"ok": True}


@chat_sessions_router.get("/sessions/{session_id}/messages", response=ChatMessagesOutSchema)
def list_chat_messages(request: HttpRequest, session_id: int):
    """GET /api/chat/sessions/{id}/messages — 拉取消息（按时间正序）。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    try:
        chat_persist.get_session_for_user(session_id=session_id, user_id=u.pk)
    except ConversationSession.DoesNotExist:
        from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

        raise HttpError(404, "会话不存在")
    rows = ConversationMessage.objects.filter(session_id=session_id).order_by("created_at")
    msgs = [
        ChatMessageOutSchema(
            id=m.pk,
            role=m.role,
            content=m.content or "",
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in rows
    ]
    return ChatMessagesOutSchema(messages=msgs)


@chat_sessions_router.post("/sessions/{session_id}/clear", response={200: dict})
def clear_chat_session_messages(request: HttpRequest, session_id: int):
    """POST /api/chat/sessions/{id}/clear — 清空当前会话消息（保留会话）。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    try:
        n = chat_persist.clear_session_messages(session_id=session_id, user_id=u.pk)
    except ConversationSession.DoesNotExist:
        from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

        raise HttpError(404, "会话不存在")
    return 200, {"ok": True, "deleted_messages": n}
