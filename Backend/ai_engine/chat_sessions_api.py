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
from ai_engine.models import AIModelCatalogEntry, LocalMediaAsset
from ai_engine.local_media_store import save_local_media_bytes
from ai_engine.integrations.ark_generative import ark_images_generate_url, ark_video_generate_poll
from ai_engine.execution_media_services import fetch_url_bytes, openai_tts_bytes

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

class ChatAttachmentInSchema(Schema):
    type: str = Field(..., description="image | video | file | audio 等")
    url: str = Field(..., description="公网可访问的 URL（或本地可访问的网关 URL）")


class ChatSendInSchema(Schema):
    content: str = Field(..., description="用户输入文本")
    model_key: str = Field(default="", description="可选：模型目录 key，如 ark-doubao-smart-router")
    attachments: list[ChatAttachmentInSchema] = Field(default_factory=list, description="可选：附件列表（目前仅图片参与多模态）")


class ChatSendOutSchema(Schema):
    ok: bool
    assistant_message: ChatMessageOutSchema | None = None
    error: str | None = None


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


@chat_sessions_router.post("/sessions/{session_id}/send", response=ChatSendOutSchema)
def send_chat_message(request: HttpRequest, session_id: int, payload: ChatSendInSchema):
    """
    POST /api/chat/sessions/{id}/send — 发送一条消息并返回助手回复（不走 workflow 图）。

    - 支持多轮上下文（会话内历史）
    - 支持图片附件（image_url 多模态）；视频/文件暂按文本链接透传，不做理解
    """
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")

    try:
        sess = chat_persist.get_session_for_user(session_id=session_id, user_id=u.pk)
    except ConversationSession.DoesNotExist:
        from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

        raise HttpError(404, "会话不存在")

    user_text = (payload.content or "").strip()
    if not user_text and not payload.attachments:
        return ChatSendOutSchema(ok=False, assistant_message=None, error="empty_input")

    # 写入用户消息，并生成对话上下文（滚动摘要 + 近期对话）
    ctx_extra, latest_query = chat_persist.append_user_and_prepare_context(session=sess, user_text=user_text or "（空消息）")
    prior = str(ctx_extra.get("_chat_prior_transcript") or "").strip()
    summary = str(ctx_extra.get("_chat_rolling_summary") or "").strip()

    # 组装 prompt（通用聊天，不绑定工作流助手人设）
    system_prompt = "你是一个通用对话助手，请直接回答用户问题。"
    parts: list[str] = []
    if summary:
        parts.append("【对话要点摘要】\n" + summary)
    if prior:
        parts.append("【近期对话摘录】\n" + prior)
    parts.append("【当前用户输入】\n" + (latest_query or user_text))
    # 非图片附件以链接形式追加，避免“丢附件”
    non_image = [a for a in (payload.attachments or []) if str(a.type or "").strip().lower() != "image"]
    if non_image:
        lines = [f"- {str(a.type).strip()}: {str(a.url).strip()}" for a in non_image if str(a.url or "").strip()]
        if lines:
            parts.append("【附件】\n" + "\n".join(lines))
    human_text = "\n\n".join([p for p in parts if p.strip()]).strip()

    # 解析模型：优先 model_key（支持 smart-router）；对于非 ark_chat 的目录项，走对应生成能力分流
    model_key = (payload.model_key or "").strip()
    route = "doubao"
    model_id = ""
    overrides: dict[str, Any] = {}
    if model_key:
        entry = AIModelCatalogEntry.objects.filter(catalog_key=model_key, is_active=True).first()
        if entry is not None and str(entry.api_kind or "") != AIModelCatalogEntry.ApiKind.ARK_CHAT:
            ak = str(entry.api_kind or "")
            mid = (entry.model_id or "").strip()
            user_prompt = (latest_query or user_text or "").strip() or human_text

            try:
                if ak == AIModelCatalogEntry.ApiKind.ARK_IMAGE_GEN:
                    if not mid:
                        raise ValueError(f"目录项「{entry.label}」未配置 model_id")
                    gen_url = ark_images_generate_url(model_id=mid, prompt=user_prompt, size="2K", watermark=False)
                    raw, ct = fetch_url_bytes(gen_url)
                    saved = save_local_media_bytes(
                        user_id=u.pk,
                        kind=LocalMediaAsset.Kind.IMAGE,
                        data=raw,
                        mime=ct or "image/png",
                        original_name="generated.png",
                        source_url=gen_url,
                    )
                    assistant_text = (
                        f"已生成图片（{entry.label}）。\n"
                        f"预览链接：{saved['public_url']}\n"
                        f"下载链接：{saved['proxy_url']}\n"
                    )
                elif ak == AIModelCatalogEntry.ApiKind.ARK_VIDEO_GEN:
                    if not mid:
                        raise ValueError(f"目录项「{entry.label}」未配置 model_id")
                    ref_img = ""
                    for a in (payload.attachments or []):
                        if str(a.type or "").strip().lower() == "image" and str(a.url or "").strip():
                            ref_img = str(a.url).strip()
                            break
                    vid_url, _raw = ark_video_generate_poll(
                        model_id=mid,
                        prompt_text=user_prompt,
                        image_url=ref_img or None,
                        duration=5,
                        resolution="720p",
                        ratio="16:9",
                        watermark=False,
                        poll_interval_s=3.0,
                        timeout_s=600.0,
                    )
                    if not vid_url:
                        raise RuntimeError("视频任务已完成但未解析到 video_url")
                    raw, ct = fetch_url_bytes(vid_url, max_bytes=80 * 1024 * 1024)
                    saved = save_local_media_bytes(
                        user_id=u.pk,
                        kind=LocalMediaAsset.Kind.VIDEO,
                        data=raw,
                        mime=ct or "video/mp4",
                        original_name="generated.mp4",
                        source_url=vid_url,
                    )
                    assistant_text = (
                        f"已生成视频（{entry.label}）。\n"
                        f"预览链接：{saved['public_url']}\n"
                        f"下载链接：{saved['proxy_url']}\n"
                    )
                elif ak == AIModelCatalogEntry.ApiKind.OPEN_SPEECH:
                    audio, ct = openai_tts_bytes(text=user_prompt, voice="alloy", response_format="mp3")
                    saved = save_local_media_bytes(
                        user_id=u.pk,
                        kind=LocalMediaAsset.Kind.AUDIO,
                        data=audio,
                        mime=ct or "audio/mpeg",
                        original_name="tts.mp3",
                        source_url="",
                    )
                    assistant_text = (
                        "已生成音频（TTS）。\n"
                        f"预览链接：{saved['public_url']}\n"
                        f"下载链接：{saved['proxy_url']}\n"
                    )
                else:
                    raise ValueError(f"暂不支持的 api_kind: {ak}")
            except Exception as exc:
                assistant_text = f"错误: {exc}"

            try:
                chat_persist.record_assistant_reply(session_id=sess.pk, content=assistant_text)
            except Exception:
                pass
            row = (
                ConversationMessage.objects.filter(session=sess, role=ConversationMessage.Role.ASSISTANT)
                .order_by("-created_at")
                .first()
            )
            if row is None:
                return ChatSendOutSchema(ok=True, assistant_message=None, error=None)
            return ChatSendOutSchema(
                ok=True,
                assistant_message=ChatMessageOutSchema(
                    id=row.pk,
                    role=row.role,
                    content=row.content or "",
                    created_at=row.created_at.isoformat() if row.created_at else "",
                ),
                error=None,
            )

        from ai_engine.ai_model_catalog import get_user_preset_llm_overrides, resolve_route_and_model_id

        route, model_id, cat_key = resolve_route_and_model_id({"modelKey": model_key}, user_id=u.pk)
        overrides = get_user_preset_llm_overrides(cat_key, u.pk)

    # 构建模型（关闭 streaming，直接返回完整回复）
    from ai_engine.workflow import get_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]

    llm = get_chat_model(route or "doubao", model=model_id, streaming=False, max_tokens=1024, **overrides)

    images = [a for a in (payload.attachments or []) if str(a.type or "").strip().lower() == "image" and str(a.url or "").strip()]
    if images:
        mm_content: list[dict[str, Any]] = [{"type": "text", "text": human_text}]
        for a in images[:4]:  # 简单限制数量，避免超长 payload
            mm_content.append({"type": "image_url", "image_url": {"url": str(a.url).strip()}})
        human_msg = HumanMessage(content=mm_content)
    else:
        human_msg = HumanMessage(content=human_text)

    try:
        resp = llm.invoke([SystemMessage(content=system_prompt), human_msg])
        assistant_text = getattr(resp, "content", str(resp)) or ""
    except Exception as exc:
        assistant_text = f"错误: {exc}"

    # 写入助手回复（并维护滚动摘要）
    try:
        chat_persist.record_assistant_reply(session_id=sess.pk, content=assistant_text)
    except Exception:
        # 即使落库失败也要返回给前端
        pass

    row = (
        ConversationMessage.objects.filter(session=sess, role=ConversationMessage.Role.ASSISTANT)
        .order_by("-created_at")
        .first()
    )
    if row is None:
        return ChatSendOutSchema(ok=True, assistant_message=None, error=None)
    return ChatSendOutSchema(
        ok=True,
        assistant_message=ChatMessageOutSchema(
            id=row.pk,
            role=row.role,
            content=row.content or "",
            created_at=row.created_at.isoformat() if row.created_at else "",
        ),
        error=None,
    )
