"""按屏幕配置与资料库表，为自动回复任务拼接系统提示附录。"""

from __future__ import annotations

from ai_engine.models import AutoReplyKnowledgeEntry, AutoReplyScreenProfile


def build_knowledge_appendix(user_id: int, input_text: str, friend_name: str = "") -> str:
    prof = AutoReplyScreenProfile.objects.filter(user_id=user_id).first()
    if not prof or not prof.knowledge_reply_enabled:
        return ""
    fn = (friend_name or "").strip()
    qs = AutoReplyKnowledgeEntry.objects.filter(user_id=user_id, is_active=True).order_by("sort_order", "id")
    pieces: list[str] = []
    for e in qs:
        if e.scope == AutoReplyKnowledgeEntry.Scope.FRIEND:
            if not fn or (e.friend_name or "").strip() != fn:
                continue
        kws = e.trigger_keywords if isinstance(e.trigger_keywords, list) else []
        if kws:
            hit = any(str(k).strip() and str(k).strip() in input_text for k in kws)
            if not hit:
                continue
        title = (e.title or "").strip() or "资料"
        pieces.append(f"### {title}\n{e.body.strip()}\n")
    if not pieces:
        return ""
    return "\n\n【本地资料库】\n" + "\n".join(pieces)
