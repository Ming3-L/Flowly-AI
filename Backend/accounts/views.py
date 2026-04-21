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
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

from rest_framework_simplejwt.tokens import RefreshToken

from ai_engine.auth import JWTAuth
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


class UserProfileSchema(Schema):
    id: int
    username: str
    email: str
    ai_model: str
    language: str
    openai_base_url: str
    is_active: bool
    date_joined: str


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
    if User.objects.filter(email=payload.email).exists():
        return 400, AuthErrorSchema(
            message="注册失败",
            detail="邮箱已被注册",
        )

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=payload.username,
                email=payload.email,
                password=payload.password,
            )
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

    return 201, UserProfileSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        ai_model="gpt-4o",
        language="zh",
        openai_base_url="",
        is_active=user.is_active,
        date_joined=user.date_joined.isoformat(),
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

    return UserProfileSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        ai_model=profile.ai_model if profile else "gpt-4o",
        language=profile.language if profile else "zh",
        openai_base_url=profile.openai_base_url if profile else "",
        is_active=user.is_active,
        date_joined=user.date_joined.isoformat(),
    )
