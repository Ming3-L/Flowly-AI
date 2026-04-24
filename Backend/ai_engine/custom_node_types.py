"""
用户自定义节点类型 CRUD。

画布 ``node_type`` 使用返回的 ``type_key``（形如 ``ut_12``）；仅所有者可读写。
"""

from __future__ import annotations

import re

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import UserCustomNodeType

custom_node_type_router = Router(tags=["User custom node types"], auth=JWTAuth())

_SLUG_RE = re.compile(r"^[a-z0-9][-a-z0-9_]{1,62}$")


class UserCustomNodeTypeCreateSchema(Schema):
    slug: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    provider_route: str = Field(
        ...,
        description="openai | doubao | ark | claude | ollama | vectorengine（与 get_chat_model 路由一致）",
    )
    model_name: str = Field(..., min_length=1, max_length=128)
    default_config: dict = Field(default_factory=dict)
    description: str = ""


class UserCustomNodeTypeUpdateSchema(Schema):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    provider_route: str | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=128)
    default_config: dict | None = None
    description: str | None = None


class UserCustomNodeTypeResponseSchema(Schema):
    id: int
    slug: str
    type_key: str
    display_name: str
    provider_route: str
    model_name: str
    default_config: dict
    description: str
    created_at: str
    updated_at: str


def _to_resp(o: UserCustomNodeType) -> UserCustomNodeTypeResponseSchema:
    return UserCustomNodeTypeResponseSchema(
        id=o.pk,
        slug=o.slug,
        type_key=o.type_key,
        display_name=o.display_name,
        provider_route=o.provider_route,
        model_name=o.model_name,
        default_config=o.default_config or {},
        description=o.description or "",
        created_at=o.created_at.isoformat() if o.created_at else "",
        updated_at=o.updated_at.isoformat() if o.updated_at else "",
    )


@custom_node_type_router.get("/", response=list[UserCustomNodeTypeResponseSchema])
def list_custom_node_types(request: HttpRequest):
    """列出当前用户的所有自定义节点类型。"""
    qs = UserCustomNodeType.objects.filter(user=request.user).order_by("-created_at")
    return [_to_resp(o) for o in qs]


@custom_node_type_router.post("/", response={201: UserCustomNodeTypeResponseSchema})
def create_custom_node_type(request: HttpRequest, payload: UserCustomNodeTypeCreateSchema):
    """创建自定义类型；前端将 ``type_key`` 写入节点 ``type`` 字段。"""
    slug = payload.slug.strip().lower()
    if not _SLUG_RE.match(slug):
        raise HttpError(400, "slug 仅允许小写字母、数字、连字符，且长度 2–63")
    pr = payload.provider_route.strip().lower()
    allowed = {c.value for c in UserCustomNodeType.ProviderRoute}
    if pr not in allowed:
        raise HttpError(400, f"provider_route 必须是: {', '.join(sorted(allowed))}")
    if UserCustomNodeType.objects.filter(user=request.user, slug=slug).exists():
        raise HttpError(400, "该 slug 已存在")
    obj = UserCustomNodeType.objects.create(
        user=request.user,
        slug=slug,
        display_name=payload.display_name.strip(),
        provider_route=pr,
        model_name=payload.model_name.strip(),
        default_config=payload.default_config or {},
        description=(payload.description or "").strip(),
    )
    return 201, _to_resp(obj)


@custom_node_type_router.get("/{type_id}", response=UserCustomNodeTypeResponseSchema)
def get_custom_node_type(request: HttpRequest, type_id: int):
    obj = get_object_or_404(UserCustomNodeType, pk=type_id, user=request.user)
    return _to_resp(obj)


@custom_node_type_router.put("/{type_id}", response=UserCustomNodeTypeResponseSchema)
def update_custom_node_type(request: HttpRequest, type_id: int, payload: UserCustomNodeTypeUpdateSchema):
    obj = get_object_or_404(UserCustomNodeType, pk=type_id, user=request.user)
    if payload.display_name is not None:
        obj.display_name = payload.display_name.strip()
    if payload.provider_route is not None:
        pr = payload.provider_route.strip().lower()
        allowed = {c.value for c in UserCustomNodeType.ProviderRoute}
        if pr not in allowed:
            raise HttpError(400, "provider_route 非法")
        obj.provider_route = pr
    if payload.model_name is not None:
        obj.model_name = payload.model_name.strip()
    if payload.default_config is not None:
        obj.default_config = payload.default_config
    if payload.description is not None:
        obj.description = payload.description
    obj.save()
    return _to_resp(obj)


@custom_node_type_router.delete("/{type_id}", response={200: dict})
def delete_custom_node_type(request: HttpRequest, type_id: int):
    obj = get_object_or_404(UserCustomNodeType, pk=type_id, user=request.user)
    obj.delete()
    return 200, {"ok": True}
