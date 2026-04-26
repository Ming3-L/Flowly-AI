"""
Authentication API — register, login, refresh, logout, current user.

All endpoints under /api/auth/ via the ai_engine NinjaAPI mount.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError
from django.http import HttpRequest
from ninja import Field, Router, Schema  # pyright: ignore[reportMissingImports]

from rest_framework_simplejwt.tokens import RefreshToken

from ai_engine.auth import JWTAuth
from ai_engine.integrations.db_platform_secrets import load_plain_entries
from .email_service import (
    issue_code,
    mark_send_cooldown,
    send_cooldown_active,
    send_verification_email,
    smtp_configured,
    verify_and_consume_code,
)
from .serializers import RegisterSchema
from .models import UserProfile

User = get_user_model()
router = Router(tags=["账户"])
logger = logging.getLogger(__name__)


# ── Schemas ─────────────────────────────────────────────────────────────────

class LoginSchema(Schema):
    username: str
    password: str


class TokenResponseSchema(Schema):
    access: str
    refresh: str | None = None
    token_type: str = "Bearer"


class AuthErrorSchema(Schema):
    message: str
    detail: str | None = None


class RefreshSchema(Schema):
    refresh: str


class OkMessageSchema(Schema):
    detail: str


class EmailSendCodeSchema(Schema):
    email: str
    purpose: str


class PasswordResetConfirmSchema(Schema):
    email: str
    code: str
    new_password: str = Field(..., min_length=8, max_length=128)
    new_password_confirm: str = Field(..., min_length=8, max_length=128)


class UserProfileSchema(Schema):
    id: int
    username: str
    email: str
    ai_model: str
    language: str
    openai_base_url: str
    nickname: str = ""
    avatar_public_url: str = ""
    is_active: bool
    date_joined: str
    is_staff: bool = False
    is_superuser: bool = False


# ── Register ────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response={
        201: UserProfileSchema,
        400: AuthErrorSchema,
        503: AuthErrorSchema,
        500: AuthErrorSchema,
    },
)
def register(request, payload: RegisterSchema):
    """
    POST /api/auth/register

    Create a new user account. Public endpoint — no auth required.
    """
    if payload.password != payload.password_confirm:
        return 400, AuthErrorSchema(
            message="注册失败",
            detail="两次输入的密码不一致",
        )
    if User.objects.filter(username=payload.username).exists():
        return 400, AuthErrorSchema(
            message="注册失败",
            detail="用户名已存在",
        )
    if User.objects.filter(email__iexact=(payload.email or "").strip()).exists():
        return 400, AuthErrorSchema(
            message="注册失败",
            detail="邮箱已被注册",
        )

    if smtp_configured():
        code = (payload.email_verification_code or "").strip()
        if len(code) != 4 or not code.isdigit():
            return 400, AuthErrorSchema(
                message="注册失败",
                detail="请先通过邮箱获取并填写 4 位数字验证码",
            )
        if not verify_and_consume_code("register", payload.email, code):
            return 400, AuthErrorSchema(
                message="注册失败",
                detail="邮箱验证码无效或已过期",
            )

    is_staff = False
    is_superuser = False
    if payload.register_as_staff:
        invite = (payload.admin_invite_code or "").strip()
        # 邀请码只允许从数据库 PlatformAIProviderSecrets（后台管理员维护）读取。
        # 特殊：若系统里还没有任何管理员账号，则允许使用默认邀请码 123456789 创建第一个超级管理员。
        secret_map = load_plain_entries()
        super_code = (secret_map.get("FLOWLY_SUPERUSER_REGISTER_INVITE") or "").strip()
        admin_code = (secret_map.get("FLOWLY_ADMIN_REGISTER_INVITE") or "").strip()
        if not invite:
            return 400, AuthErrorSchema(
                message="注册失败",
                detail="注册管理员账号需要填写邀请码",
            )
        any_admin = User.objects.filter(is_superuser=True).exists() or User.objects.filter(is_staff=True).exists()
        if not any_admin and invite == "123456789":
            is_staff = True
            is_superuser = True
        elif super_code and invite == super_code:
            is_staff = True
            is_superuser = True
        elif admin_code and invite == admin_code:
            is_staff = True
            is_superuser = False
        else:
            if not super_code and not admin_code:
                detail = (
                    "管理员自助注册未开放：后台「接入配置 (密钥)」未设置 "
                    "FLOWLY_ADMIN_REGISTER_INVITE / FLOWLY_SUPERUSER_REGISTER_INVITE。"
                )
            else:
                detail = "管理员邀请码无效。"
            return 400, AuthErrorSchema(message="注册失败", detail=detail)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=payload.username,
                email=payload.email,
                password=payload.password,
                is_staff=is_staff,
            )
            if is_superuser:
                user.is_superuser = True
                user.save(update_fields=["is_superuser"])
            UserProfile.objects.create(user=user)
    except IntegrityError:
        # 并发或唯一约束冲突时 exists() 检查挡不住
        return 400, AuthErrorSchema(
            message="注册失败",
            detail="用户名或邮箱已被占用",
        )
    except OperationalError:
        logger.exception("register: database unavailable")
        return 503, AuthErrorSchema(
            message="注册失败",
            detail="无法连接数据库，请确认 MySQL 已启动且 DATABASE_URL 配置正确",
        )
    except Exception as exc:
        logger.exception("register: unexpected error")
        detail = str(exc) if settings.DEBUG else "服务器繁忙，请稍后重试"
        return 500, AuthErrorSchema(
            message="注册失败",
            detail=detail,
        )

    user.refresh_from_db()
    return 201, UserProfileSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        ai_model="ark-doubao-smart-router",
        language="zh",
        openai_base_url="",
        is_active=user.is_active,
        date_joined=user.date_joined.isoformat(),
        is_staff=bool(user.is_staff),
        is_superuser=bool(user.is_superuser),
    )


# ── Login ───────────────────────────────────────────────────────────────────

@router.post("/login", response={200: TokenResponseSchema, 401: AuthErrorSchema})
def login(request: HttpRequest, payload: LoginSchema):
    """
    POST /api/auth/login

    Authenticate with username + password, return JWT tokens.
    Public endpoint — no auth required.
    """
    try:
        user = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        return 401, AuthErrorSchema(
            message="认证失败",
            detail="用户名或密码错误",
        )

    if not check_password(payload.password, user.password):
        return 401, AuthErrorSchema(
            message="认证失败",
            detail="用户名或密码错误",
        )

    if not user.is_active:
        return 401, AuthErrorSchema(
            message="认证失败",
            detail="账户已被禁用",
        )

    refresh = RefreshToken.for_user(user)
    return 200, TokenResponseSchema(
        access=str(refresh.access_token),
        refresh=str(refresh),
    )


# ── Token Refresh ─────────────────────────────────────────────────────────

@router.post("/refresh", response={200: TokenResponseSchema, 401: AuthErrorSchema})
def refresh_token(request: HttpRequest, payload: RefreshSchema):
    """
    POST /api/auth/refresh

    Exchange a valid refresh token for a new access token.
    Public endpoint — no auth required.
    """
    try:
        refresh = RefreshToken(payload.refresh)
    except Exception:
        return 401, AuthErrorSchema(
            message="令牌刷新失败",
            detail="无效或已过期的刷新令牌",
        )

    return 200, TokenResponseSchema(
        access=str(refresh.access_token),
        refresh=str(refresh),
    )


# ── Logout ─────────────────────────────────────────────────────────────────

@router.post("/logout", response=Schema)
def logout(request: HttpRequest, payload: RefreshSchema):
    """
    POST /api/auth/logout

    Log out by blacklisting the refresh token.
    """
    try:
        refresh = RefreshToken(payload.refresh)
        refresh.blacklist()
    except Exception:
        pass

    return {"detail": "已成功登出"}


# ── Current User ───────────────────────────────────────────────────────────

@router.get("/me", response=UserProfileSchema, auth=JWTAuth())
def get_me(request: HttpRequest):
    """
    GET /api/auth/me

    Return the currently authenticated user's full profile.
    Requires JWT Bearer token.
    """
    user: User = request.user  # injected by bearer_auth dependency

    profile = getattr(user, "profile", None)

    from ai_engine.local_media_store import build_public_url

    nick = ""
    avatar_url = ""
    if profile:
        nick = (getattr(profile, "nickname", "") or "").strip()
        ap = (getattr(profile, "avatar_path", "") or "").strip()
        if ap:
            avatar_url = build_public_url(ap)

    return UserProfileSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        ai_model=profile.ai_model if profile else "ark-doubao-smart-router",
        language=profile.language if profile else "zh",
        openai_base_url=profile.openai_base_url if profile else "",
        nickname=nick,
        avatar_public_url=avatar_url,
        is_active=user.is_active,
        date_joined=user.date_joined.isoformat(),
        is_staff=bool(getattr(user, "is_staff", False)),
        is_superuser=bool(getattr(user, "is_superuser", False)),
    )


# ── Email verification & password reset ─────────────────────────────────────


@router.post(
    "/email/send-code",
    response={200: OkMessageSchema, 400: AuthErrorSchema, 503: AuthErrorSchema},
)
def send_email_code(request: HttpRequest, payload: EmailSendCodeSchema):
    """
    POST /api/auth/email/send-code

    发送 4 位数字验证码（注册或找回密码）。SMTP 须在后台「接入配置」写入库内 ``FLOWLY_SMTP_*``。
    """
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email

    email = (payload.email or "").strip()
    purpose = (payload.purpose or "").strip().lower()
    if purpose not in ("register", "password_reset"):
        return 400, AuthErrorSchema(message="发送失败", detail="purpose 须为 register 或 password_reset")

    try:
        validate_email(email)
    except ValidationError:
        return 400, AuthErrorSchema(message="发送失败", detail="邮箱格式无效")

    if not smtp_configured():
        return 503, AuthErrorSchema(
            message="发送失败",
            detail="管理员尚未在后台「接入配置 (密钥)」中填写 FLOWLY_SMTP_HOST、FLOWLY_SMTP_USER、FLOWLY_SMTP_PASSWORD",
        )

    if send_cooldown_active(purpose, email):
        return 400, AuthErrorSchema(message="发送失败", detail="发送过于频繁，请约 1 分钟后再试")

    if purpose == "register":
        if User.objects.filter(email__iexact=email).exists():
            return 400, AuthErrorSchema(message="发送失败", detail="该邮箱已注册")

    if purpose == "password_reset":
        if not User.objects.filter(email__iexact=email).exists():
            return 200, OkMessageSchema(detail="若该邮箱已注册，您将很快收到验证码邮件")

    code = issue_code(purpose, email)
    try:
        send_verification_email(purpose=purpose, to_email=email, code=code)
    except Exception:
        logger.exception("send_email_code: SMTP failure")
        return 503, AuthErrorSchema(message="发送失败", detail="邮件发送失败，请稍后重试或检查 SMTP 配置")

    mark_send_cooldown(purpose, email)
    return 200, OkMessageSchema(detail="验证码已发送，请查收邮箱")


@router.post(
    "/password/reset/confirm",
    response={200: OkMessageSchema, 400: AuthErrorSchema, 503: AuthErrorSchema},
)
def password_reset_confirm(request: HttpRequest, payload: PasswordResetConfirmSchema):
    """
    POST /api/auth/password/reset/confirm

    使用邮箱收到的 4 位验证码重置密码。
    """
    if payload.new_password != payload.new_password_confirm:
        return 400, AuthErrorSchema(message="重置失败", detail="两次输入的新密码不一致")

    if not smtp_configured():
        return 503, AuthErrorSchema(
            message="重置失败",
            detail="管理员尚未在后台配置库内发信项 FLOWLY_SMTP_*，无法使用邮箱重置密码",
        )

    email = (payload.email or "").strip()
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        return 400, AuthErrorSchema(message="重置失败", detail="验证码无效或已过期")

    if not verify_and_consume_code("password_reset", email, payload.code):
        return 400, AuthErrorSchema(message="重置失败", detail="验证码无效或已过期")

    user.set_password(payload.new_password)
    user.save(update_fields=["password"])
    return 200, OkMessageSchema(detail="密码已重置，请使用新密码登录")
