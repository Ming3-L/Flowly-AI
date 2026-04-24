"""
对话会话持久化：与独立「AI 对话页」配合，限制每用户会话数、拼接多轮上下文、维护滚动摘要。
"""

from __future__ import annotations

import re
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from ai_engine.models import ConversationMessage, ConversationSession

MAX_SESSIONS_PER_USER = 50
MAX_TRANSCRIPT_CHARS = 12_000
MAX_PAIRS_IN_TRANSCRIPT = 18
ROLLING_SUMMARY_MAX = 2000
SNIPPET_LEN = 160


def _snippet(text: str, n: int = SNIPPET_LEN) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= n:
        return t
    return t[: n - 1] + "…"


def enforce_session_count(*, user: User) -> None:
    """超过上限时删除最旧的会话（级联删消息）。"""
    qs = ConversationSession.objects.filter(user=user).order_by("-created_at")
    ids = list(qs.values_list("pk", flat=True))
    if len(ids) <= MAX_SESSIONS_PER_USER:
        return
    overflow = ids[MAX_SESSIONS_PER_USER :]
    ConversationSession.objects.filter(pk__in=overflow).delete()


def get_session_for_user(*, session_id: int, user_id: int) -> ConversationSession:
    return ConversationSession.objects.get(pk=session_id, user_id=user_id)


@transaction.atomic
def create_session(*, user: User, topic: str = "") -> ConversationSession:
    enforce_session_count(user=user)
    return ConversationSession.objects.create(
        user=user,
        topic=(topic or "")[:255],
        metadata={},
    )


@transaction.atomic
def append_message(*, session: ConversationSession, role: str, content: str, metadata: dict | None = None) -> ConversationMessage:
    return ConversationMessage.objects.create(
        session=session,
        role=role,
        content=content or "",
        metadata=metadata or {},
    )


def build_prior_transcript(*, session_id: int, exclude_last_n: int = 1) -> str:
    """
    将最近若干轮 user/assistant 拼成文本块，供模型理解「上文」。

    exclude_last_n：通常为 1，表示排除刚写入的最后一条（当前用户句），
    由调用方把「当前用户」单独放在 query 里，避免重复。
    """
    qs = (
        ConversationMessage.objects.filter(session_id=session_id)
        .order_by("-created_at")
        .values_list("role", "content")[: max(1, MAX_PAIRS_IN_TRANSCRIPT * 2 + exclude_last_n + 5)]
    )
    rows = list(qs)
    if exclude_last_n > 0:
        rows = rows[exclude_last_n:]
    rows.reverse()
    lines: list[str] = []
    total = 0
    for role, content in rows:
        if role not in (ConversationMessage.Role.USER, ConversationMessage.Role.ASSISTANT):
            continue
        label = "用户" if role == ConversationMessage.Role.USER else "助手"
        piece = f"{label}: {_snippet(content or '')}"
        if total + len(piece) > MAX_TRANSCRIPT_CHARS:
            lines.append("…（更早内容已省略）")
            break
        lines.append(piece)
        total += len(piece) + 1
    return "\n".join(lines).strip()


@transaction.atomic
def append_user_and_prepare_context(*, session: ConversationSession, user_text: str) -> tuple[dict[str, Any], str]:
    """
    写入用户消息，返回 (要合并进 workflow context 的 dict, 当前用户一句原文)。
    """
    append_message(session=session, role=ConversationMessage.Role.USER, content=user_text)
    session.topic = (session.topic or "").strip() or _snippet(user_text, 40)
    md = dict(session.metadata or {})
    summary = str(md.get("rolling_summary") or "").strip()
    prior = build_prior_transcript(session_id=session.pk, exclude_last_n=1)
    session.metadata = md
    session.save(update_fields=["topic", "metadata", "updated_at"])
    ctx: dict[str, Any] = {
        "_chat_prior_transcript": prior,
        "_chat_rolling_summary": summary,
    }
    return ctx, user_text


@transaction.atomic
def record_assistant_reply(*, session_id: int, content: str) -> None:
    """执行成功后写入助手回复并更新滚动摘要（轻量拼接，非二次模型调用）。"""
    sess = ConversationSession.objects.select_for_update().get(pk=session_id)
    append_message(session=sess, role=ConversationMessage.Role.ASSISTANT, content=content or "")
    md = dict(sess.metadata or {})
    prev = str(md.get("rolling_summary") or "").strip()
    last_user = (
        ConversationMessage.objects.filter(session=sess, role=ConversationMessage.Role.USER)
        .order_by("-created_at")
        .values_list("content", flat=True)
        .first()
    )
    u_snip = _snippet(str(last_user or ""), 120)
    a_snip = _snippet(content or "", 120)
    line = f"[{timezone.now().strftime('%m-%d %H:%M')}] 用户:{u_snip} | 助手:{a_snip}"
    merged = (prev + "\n" + line).strip() if prev else line
    if len(merged) > ROLLING_SUMMARY_MAX:
        merged = merged[-ROLLING_SUMMARY_MAX:]
    md["rolling_summary"] = merged
    sess.metadata = md
    sess.save(update_fields=["metadata", "updated_at"])


@transaction.atomic
def remove_last_message_if_role(*, session_id: int, user_id: int, role: str) -> bool:
    """执行失败时回滚刚追加的用户句（仅当最后一条匹配 role）。"""
    sess = get_session_for_user(session_id=session_id, user_id=user_id)
    last = ConversationMessage.objects.filter(session=sess).order_by("-created_at").first()
    if last is None or last.role != role:
        return False
    last.delete()
    return True


def clear_session_messages(*, session_id: int, user_id: int) -> int:
    """清空会话内消息；返回删除条数。"""
    sess = get_session_for_user(session_id=session_id, user_id=user_id)
    n, _ = ConversationMessage.objects.filter(session=sess).delete()
    ConversationSession.objects.filter(pk=sess.pk).update(metadata={}, topic="")
    return n
