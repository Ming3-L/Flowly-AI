"""
平台管理后台 API —— 仅 is_staff / is_superuser 可访问。
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]

from ai_engine.auth import JWTAuth
from ai_engine.integrations.db_platform_secrets import merge_entries_patch, seed_from_process_environ
from ai_engine.integrations.secrets_loader import describe_managed_keys_for_admin, managed_ai_config_key_names
from ai_engine.models import LocalMediaAsset
from pydantic import Field  # pyright: ignore[reportMissingImports]

User = get_user_model()
admin_router = Router(tags=["Admin Portal"], auth=JWTAuth())


def _require_platform_staff(request: HttpRequest) -> None:
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    u = getattr(request, "auth", None)
    if u is None:
        raise HttpError(401, "需要登录")
    if not (bool(getattr(u, "is_staff", False)) or bool(getattr(u, "is_superuser", False))):
        raise HttpError(403, "需要管理员权限（is_staff 或 is_superuser）")


class AdminUserRowSchema(Schema):
    id: int
    username: str
    email: str
    is_staff: bool
    is_superuser: bool
    is_active: bool
    date_joined: str


class AdminUserListOutSchema(Schema):
    total: int
    items: list[AdminUserRowSchema]


@admin_router.get("/users", response=AdminUserListOutSchema)
def list_users(request: HttpRequest, page: int = 1, page_size: int = 20):
    """分页列出所有用户（管理员）。"""
    _require_platform_staff(request)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    qs = User.objects.all().order_by("-date_joined")
    total = qs.count()
    start = (page - 1) * page_size
    items: list[AdminUserRowSchema] = []
    for u in qs[start : start + page_size]:
        items.append(
            AdminUserRowSchema(
                id=int(u.pk),
                username=str(u.username or ""),
                email=str(u.email or ""),
                is_staff=bool(u.is_staff),
                is_superuser=bool(u.is_superuser),
                is_active=bool(u.is_active),
                date_joined=u.date_joined.isoformat() if u.date_joined else "",
            )
        )
    return AdminUserListOutSchema(total=total, items=items)


class AdminMediaRowSchema(Schema):
    id: int
    user_id: int
    username: str
    kind: str
    mime: str
    size_bytes: int
    original_name: str
    rel_path: str
    created_at: str


class AdminMediaListOutSchema(Schema):
    total: int
    items: list[AdminMediaRowSchema]


@admin_router.get("/media", response=AdminMediaListOutSchema)
def list_media_assets(request: HttpRequest, page: int = 1, page_size: int = 20, kind: str = ""):
    """分页列出本地媒体资源元数据（管理员）。"""
    _require_platform_staff(request)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    qs = LocalMediaAsset.objects.all().select_related("user").order_by("-created_at")
    k = (kind or "").strip()
    if k:
        qs = qs.filter(kind=k)
    total = qs.count()
    start = (page - 1) * page_size
    items: list[AdminMediaRowSchema] = []
    for r in qs[start : start + page_size]:
        uname = ""
        if getattr(r, "user", None):
            uname = str(getattr(r.user, "username", "") or "")
        items.append(
            AdminMediaRowSchema(
                id=int(r.pk),
                user_id=int(r.user_id),
                username=uname or str(r.user_id),
                kind=str(r.kind or ""),
                mime=str(r.mime or ""),
                size_bytes=int(r.size_bytes or 0),
                original_name=str(r.original_name or ""),
                rel_path=str(r.rel_path or ""),
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
        )
    return AdminMediaListOutSchema(total=total, items=items)


class AIProviderSecretStatusRowSchema(Schema):
    key: str
    winning_source: str
    is_effective_non_empty: bool


class AIProviderSecretsStatusOutSchema(Schema):
    items: list[AIProviderSecretStatusRowSchema]


@admin_router.get("/ai-provider-secrets/status", response=AIProviderSecretsStatusOutSchema)
def ai_provider_secrets_status(request: HttpRequest):
    """
    平台 AI 接入配置项状态（不返回明文）。
    ``winning_source``: database | environment | local_file | default
    """
    _require_platform_staff(request)
    raw = describe_managed_keys_for_admin()
    return AIProviderSecretsStatusOutSchema(
        items=[AIProviderSecretStatusRowSchema(**row) for row in raw]
    )


class AIProviderSecretsPatchIn(Schema):
    """仅允许 ``managed_ai_config_key_names`` 中的 key；空字符串表示删除库内覆盖。"""

    entries: dict[str, str] = Field(default_factory=dict)


@admin_router.patch("/ai-provider-secrets", response=AIProviderSecretsStatusOutSchema)
def ai_provider_secrets_patch(request: HttpRequest, payload: AIProviderSecretsPatchIn):
    _require_platform_staff(request)
    allowed = set(managed_ai_config_key_names())
    for k in payload.entries:
        if k not in allowed:
            from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

            raise HttpError(400, f"未知配置键: {k}")
    merge_entries_patch(dict(payload.entries))
    raw = describe_managed_keys_for_admin()
    return AIProviderSecretsStatusOutSchema(
        items=[AIProviderSecretStatusRowSchema(**row) for row in raw]
    )


class ImportAIProviderSecretsFromEnvIn(Schema):
    replace: bool = Field(default=False, description="为 true 时先清空库内项再写入")


class ImportAIProviderSecretsFromEnvOutSchema(Schema):
    ok: bool
    imported_count: int
    items: list[AIProviderSecretStatusRowSchema]


@admin_router.post(
    "/ai-provider-secrets/import-from-env",
    response=ImportAIProviderSecretsFromEnvOutSchema,
)
def ai_provider_secrets_import_from_env(request: HttpRequest, payload: ImportAIProviderSecretsFromEnvIn):
    """将当前进程已加载的非空环境变量写入数据库（便于从 .env 迁库）。"""
    _require_platform_staff(request)
    n = seed_from_process_environ(replace=bool(payload.replace))
    raw = describe_managed_keys_for_admin()
    return ImportAIProviderSecretsFromEnvOutSchema(
        ok=True,
        imported_count=n,
        items=[AIProviderSecretStatusRowSchema(**row) for row in raw],
    )
