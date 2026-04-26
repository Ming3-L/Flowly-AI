"""
邮箱验证码：注册 / 找回密码。

SMTP 参数**仅**从数据库 ``PlatformAIProviderSecrets``（管理员在后台「接入配置」维护）读取，
不使用 .env 中的 EMAIL_*。

正文由已配置的**文本对话模型**（方舟 ``get_chat_model("doubao")``）生成，且必须包含系统生成的 4 位验证码；
模型失败时回退为固定模板正文。
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from django.core.cache import cache
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)

CODE_TTL_SEC = 600
SEND_COOLDOWN_SEC = 60


def _smtp_entries_from_database_only() -> dict[str, str]:
    """只读库内解密项，不合并环境变量 / project_secrets_local。"""
    from ai_engine.integrations.db_platform_secrets import load_plain_entries

    return load_plain_entries()


def load_smtp_config_from_database() -> dict[str, Any] | None:
    """
    从 ``PlatformAIProviderSecrets`` 解析 SMTP。必须同时配置 HOST、USER、PASSWORD。
    """
    e = _smtp_entries_from_database_only()
    host = (e.get("FLOWLY_SMTP_HOST") or "").strip()
    user = (e.get("FLOWLY_SMTP_USER") or "").strip()
    password = (e.get("FLOWLY_SMTP_PASSWORD") or "").strip()
    if not (host and user and password):
        return None
    port_raw = (e.get("FLOWLY_SMTP_PORT") or "465").strip()
    try:
        port = int(port_raw)
    except ValueError:
        port = 465
    ssl_flag = (e.get("FLOWLY_SMTP_USE_SSL") or "").strip().lower() in ("1", "true", "yes", "on")
    tls_flag = (e.get("FLOWLY_SMTP_USE_TLS") or "").strip().lower() in ("1", "true", "yes", "on")
    if ssl_flag:
        use_ssl, use_tls = True, False
    elif tls_flag:
        use_ssl, use_tls = False, True
    elif port == 465:
        use_ssl, use_tls = True, False
    else:
        use_ssl, use_tls = False, True
    from_email = (e.get("FLOWLY_SMTP_FROM_EMAIL") or "").strip() or user
    return {
        "host": host,
        "port": port,
        "username": user,
        "password": password,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "from_email": from_email,
    }


def smtp_configured() -> bool:
    return load_smtp_config_from_database() is not None


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _code_cache_key(purpose: str, email: str) -> str:
    return f"flowly:email_code:{purpose}:{_norm_email(email)}"


def _cooldown_cache_key(purpose: str, email: str) -> str:
    return f"flowly:email_send_cd:{purpose}:{_norm_email(email)}"


def issue_code(purpose: str, email: str) -> str:
    code = f"{secrets.randbelow(10000):04d}"
    cache.set(_code_cache_key(purpose, email), code, CODE_TTL_SEC)
    return code


def verify_and_consume_code(purpose: str, email: str, code: str) -> bool:
    raw = (code or "").strip()
    if len(raw) != 4 or not raw.isdigit():
        return False
    key = _code_cache_key(purpose, email)
    stored = cache.get(key)
    if not stored or stored != raw:
        return False
    cache.delete(key)
    return True


def send_cooldown_active(purpose: str, email: str) -> bool:
    return bool(cache.get(_cooldown_cache_key(purpose, email)))


def mark_send_cooldown(purpose: str, email: str) -> None:
    cache.set(_cooldown_cache_key(purpose, email), "1", SEND_COOLDOWN_SEC)


def _fallback_plain_body(*, purpose: str, code: str) -> str:
    if purpose == "register":
        return (
            f"您好，\n\n您在 Flowly 的注册验证码为：{code} ，{CODE_TTL_SEC // 60} 分钟内有效。\n"
            "如非本人操作请忽略本邮件。\n"
        )
    return (
        f"您好，\n\n您正在重置 Flowly 账户密码。验证码：{code} ，{CODE_TTL_SEC // 60} 分钟内有效。\n"
        "如非本人操作请忽略本邮件并及时检查账号安全。\n"
    )


def _compose_body_with_ai(*, purpose: str, recipient_email: str, code: str) -> str:
    """
    使用方舟文本模型撰写邮件正文；正文中必须包含验证码四位数字。
    """
    scene = "用户注册 Flowly 账号" if purpose == "register" else "用户通过邮箱重置 Flowly 登录密码"
    prompt = (
        f"场景：{scene}。\n"
        f"收件人邮箱：{recipient_email}\n"
        f"系统生成的验证码（你必须在正文中原样写出这四位数字，不要改写顺序或位数）：{code}\n"
        f"验证码有效期：{CODE_TTL_SEC // 60} 分钟。\n\n"
        "请写一封简洁、友好的中文**纯文本**邮件正文（不要写主题行、不要使用 HTML、不要加 Markdown）。\n"
        "要求：语气专业可信；便于用户阅读；除上述验证码外不要编造其它数字代码。\n"
        "只输出邮件正文本身。"
    )
    try:
        from langchain_core.messages import HumanMessage

        from ai_engine.workflow import get_chat_model

        llm = get_chat_model("doubao", temperature=0.35, streaming=False, max_tokens=768)
        out = llm.invoke([HumanMessage(content=prompt)])
        body = (getattr(out, "content", None) or "").strip()
        if len(body) < 8:
            return _fallback_plain_body(purpose=purpose, code=code)
        if code not in body:
            body = f"{body}\n\n验证码：{code}\n"
        return body
    except Exception:
        logger.exception("verification email: AI compose failed, using template body")
        return _fallback_plain_body(purpose=purpose, code=code)


def _verification_subject(purpose: str) -> str:
    return "Flowly 注册验证码" if purpose == "register" else "Flowly 重置密码验证码"


def send_verification_email(*, purpose: str, to_email: str, code: str) -> None:
    cfg = load_smtp_config_from_database()
    if not cfg:
        raise RuntimeError("SMTP 未在数据库中配置（FLOWLY_SMTP_HOST / USER / PASSWORD）")

    subject = _verification_subject(purpose)
    body = _compose_body_with_ai(purpose=purpose, recipient_email=to_email.strip(), code=code)

    conn = EmailBackend(
        host=cfg["host"],
        port=int(cfg["port"]),
        username=cfg["username"],
        password=cfg["password"],
        use_tls=bool(cfg["use_tls"]),
        use_ssl=bool(cfg["use_ssl"]),
        fail_silently=False,
    )
    msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=cfg["from_email"],
        to=[to_email.strip()],
        connection=conn,
    )
    msg.encoding = "utf-8"
    msg.send()
