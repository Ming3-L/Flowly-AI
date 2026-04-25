"""
同步执行一条 AutoReplyJob：解析模型、调用 LangChain Chat、写回数据库。

由 Celery 任务或独立 spawn 子进程调用，避免阻塞 Django 请求线程。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]

from ai_engine.ai_model_catalog import get_user_preset_llm_overrides, resolve_route_and_model_id
from ai_engine.auto_reply.knowledge_merge import build_knowledge_appendix
from ai_engine.auto_reply.presets import compose_style_system_prompt
from ai_engine.models import AutoReplyChatHistoryEntry, AutoReplyJob, AutoReplyRule, AutoReplyScreenProfile
from ai_engine.workflow import get_chat_model

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM = (
    "你是专业客服与运营助手。根据用户给出的「客户消息」生成一条可直接发送给客户的回复："
    "语气礼貌、信息准确、简洁。只输出回复正文，不要前缀说明或 Markdown 标题。"
)

_SUSPICIOUS_REPLY_RE = re.compile(r"^[\s\W]*[【】\[\]\(\)\{\}<>《》「」『』（）]*[\s\W]*$")


def _is_suspicious_reply(text: str) -> bool:
    """
    自动发送场景下，LLM 偶发会返回空串/纯符号（例如 `【】【】`）。
    这种内容直接发出去体验很差，因此视为失败并让上层不发送。
    """
    t = str(text or "").strip()
    if not t:
        return True
    # 纯括号/符号/空白
    if _SUSPICIOUS_REPLY_RE.fullmatch(t):
        return True
    # 极短且无中文/字母数字，基本不可用
    core = re.sub(r"\s+", "", t)
    if len(core) <= 2 and not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", core):
        return True
    return False


def _effective_model_key(rule: AutoReplyRule | None, *, friend_model_key: str = "") -> str:
    fk = (friend_model_key or "").strip()
    if fk:
        return fk
    r = (rule.model_key if rule and (rule.model_key or "").strip() else "").strip()
    if r:
        return r
    g = str(getattr(settings, "FLOWLY_AUTO_REPLY_MODEL_KEY", "") or "").strip()
    return g or "gpt-4o"


def run_auto_reply_job_sync(job_id: int) -> None:
    """从 DB 取任务，置为 processing，调用 LLM，写入 reply 或 error。"""
    with transaction.atomic():
        job = (
            AutoReplyJob.objects.select_for_update()
            .select_related("rule", "user")
            .filter(pk=job_id)
            .first()
        )
        if job is None:
            return
        if job.status not in (AutoReplyJob.Status.PENDING, AutoReplyJob.Status.PROCESSING):
            return
        job.status = AutoReplyJob.Status.PROCESSING
        job.save(update_fields=["status", "updated_at"])

    rule: AutoReplyRule | None = job.rule if job.rule_id else None
    if rule is not None and rule.user_id != job.user_id:
        rule = None

    # —— 优先级：好友覆盖(custom_system_prompt/personality/scene) > 规则自定义system_prompt > 规则人格/情景 > 默认system
    fn = (getattr(job, "friend_name", "") or "").strip()
    friend_model_key = ""
    friend_style_prompt = ""
    if fn:
        try:
            sp = AutoReplyScreenProfile.objects.filter(user_id=int(job.user_id)).first()
            fo = sp.friends_overrides if sp and isinstance(sp.friends_overrides, dict) else {}
            o = fo.get(fn) if isinstance(fo, dict) else None
            if isinstance(o, dict):
                friend_model_key = str(o.get("model_key") or "").strip()
                csp = str(o.get("custom_system_prompt") or "").strip()
                if csp:
                    friend_style_prompt = csp
                else:
                    pk = str(o.get("personality") or o.get("personality_key") or "").strip()
                    sk = str(o.get("scene") or o.get("scene_key") or "").strip()
                    friend_style_prompt = compose_style_system_prompt(pk, sk) or ""
        except Exception:
            friend_model_key = ""
            friend_style_prompt = ""

    if friend_style_prompt:
        system_prompt = friend_style_prompt
    else:
        custom = (rule.system_prompt if rule else "").strip()
        if custom:
            system_prompt = custom
        else:
            combo = compose_style_system_prompt(
                rule.personality_key if rule else "",
                rule.scene_key if rule else "",
            )
            system_prompt = combo or _DEFAULT_SYSTEM
    appendix = build_knowledge_appendix(
        int(job.user_id),
        (job.input_text or "").strip(),
        getattr(job, "friend_name", "") or "",
    )
    if appendix:
        system_prompt = (system_prompt or "").rstrip() + appendix

    mk = _effective_model_key(rule, friend_model_key=friend_model_key)
    uid = int(job.user_id)

    try:
        route, model_id, cat_key = resolve_route_and_model_id({"modelKey": mk}, user_id=uid)
        overrides = get_user_preset_llm_overrides(cat_key, uid)
        llm = get_chat_model(
            route,
            model=model_id,
            temperature=0.5,
            max_tokens=2048,
            streaming=False,
            **overrides,
        )
        user_block = f"客户消息：\n{(job.input_text or '').strip()}"
        resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_block)])
        text = getattr(resp, "content", str(resp)) or ""
        text = str(text).strip()
        if _is_suspicious_reply(text):
            raise ValueError(f"LLM 输出疑似无效：{text!r}")
        with transaction.atomic():
            j2 = AutoReplyJob.objects.select_for_update().get(pk=job_id)
            j2.reply_text = text
            j2.model_key_used = mk
            j2.status = AutoReplyJob.Status.COMPLETED
            j2.updated_at = timezone.now()
            j2.save(update_fields=["reply_text", "model_key_used", "status", "updated_at"])
        try:
            fn2 = (getattr(job, "friend_name", "") or "").strip()
            AutoReplyChatHistoryEntry.objects.create(
                user_id=uid,
                friend_name=fn2,
                role=AutoReplyChatHistoryEntry.Role.USER,
                content=(job.input_text or "").strip()[:32000],
                meta={"source": "auto_reply_job", "job_id": job_id},
            )
            AutoReplyChatHistoryEntry.objects.create(
                user_id=uid,
                friend_name=fn2,
                role=AutoReplyChatHistoryEntry.Role.ASSISTANT,
                content=text[:32000],
                meta={"source": "auto_reply_job", "job_id": job_id, "model_key": mk},
            )
        except Exception:
            logger.exception("auto_reply job %s: chat history persist failed", job_id)
    except Exception as exc:
        logger.exception("auto_reply job %s failed", job_id)
        with transaction.atomic():
            j2 = AutoReplyJob.objects.select_for_update().get(pk=job_id)
            j2.status = AutoReplyJob.Status.FAILED
            j2.error_message = str(exc)[:4000]
            j2.updated_at = timezone.now()
            j2.save(update_fields=["status", "error_message", "updated_at"])


def run_auto_reply_job_in_subprocess(job_id: int) -> None:
    """Windows/Linux 下 spawn 独立进程，避免与主 worker 争抢 GIL（需已配置 DJANGO_SETTINGS_MODULE）。"""
    import multiprocessing as mp

    def _entry(jid: int) -> None:
        import os

        import django

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flowly_backend.settings")
        django.setup()
        run_auto_reply_job_sync(jid)

    ctx = mp.get_context("spawn")
    p = ctx.Process(target=_entry, args=(job_id,), name=f"auto-reply-{job_id}")
    p.daemon = True
    p.start()
