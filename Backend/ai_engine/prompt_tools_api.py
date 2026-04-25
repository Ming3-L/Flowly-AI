from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from ai_engine.ai_model_catalog import (
    get_user_preset_llm_overrides,
    list_models_merged_for_api,
    resolve_route_and_model_id,
)
from ai_engine.auth import JWTAuth
from ai_engine.integrations import get_ai_provider_settings
from ai_engine.models import (
    AIModelCatalogEntry,
    AIModelVariant,
    PromptEnhancementRecord,
    UserChatModelPreset,
    Workflow,
)
from ai_engine.workflow import get_chat_model


ai_router = Router(tags=["AI Catalog"], auth=JWTAuth())
prompt_tools_router = Router(tags=["Prompt Tools"], auth=JWTAuth())


class AIModelEntrySchema(Schema):
    key: str
    label: str
    description: str
    route: str
    modalities: list[str] = Field(
        default_factory=list,
        description="支持的输入模态：text/image/audio/video（用于前端控制附件发送）",
    )
    source: str = Field(
        default="project",
        description="catalog=数据库目录；project=代码内置；user=当前用户自定义",
    )
    category: str = ""
    category_label: str = ""
    category_order: int = 0
    scopes: list[str] = Field(default_factory=list)
    scope_summary: str = ""
    has_custom_credentials: bool = False
    # 画布节点模型下拉：仅出现在这些节点类型；canvas_universal 时全节点可见
    canvas_node_kinds: list[str] = Field(default_factory=list)
    canvas_universal: bool = False
    api_kind: str = Field(default="ark_chat", description="ark_chat / ark_embedding / …")
    show_in_canvas_llm_nodes: bool = True


class AIModelsCatalogSchema(Schema):
    models: list[AIModelEntrySchema]


def _require_staff(request: HttpRequest) -> None:
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    u = getattr(request, "auth", None)
    if u is None or not (
        bool(getattr(u, "is_staff", False)) or bool(getattr(u, "is_superuser", False))
    ):
        raise HttpError(403, "需要管理员（is_staff 或 is_superuser）权限")


class AIModelCatalogEntryOutSchema(Schema):
    id: int
    catalog_key: str
    label: str
    description: str
    route: str
    model_id: str
    category: str
    category_label: str
    category_order: int
    sort_order: int
    scopes: list[str]
    scope_summary: str
    canvas_node_kinds: list[str]
    canvas_universal: bool
    api_kind: str
    show_in_canvas_llm_nodes: bool
    is_active: bool


def _catalog_entry_to_out(o: AIModelCatalogEntry) -> AIModelCatalogEntryOutSchema:
    return AIModelCatalogEntryOutSchema(
        id=o.pk,
        catalog_key=o.catalog_key,
        label=o.label,
        description=o.description or "",
        route=o.route,
        model_id=o.model_id or "",
        category=o.category,
        category_label=o.category_label,
        category_order=int(o.category_order or 0),
        sort_order=int(o.sort_order or 0),
        scopes=list(o.scopes or []),
        scope_summary=o.scope_summary or "",
        canvas_node_kinds=list(o.canvas_node_kinds or []),
        canvas_universal=bool(o.canvas_universal),
        api_kind=o.api_kind,
        show_in_canvas_llm_nodes=bool(o.show_in_canvas_llm_nodes),
        is_active=bool(o.is_active),
    )


class AIModelCatalogEntryCreateSchema(Schema):
    catalog_key: str = Field(..., min_length=2, max_length=96)
    label: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=512)
    route: str = Field(default="doubao", max_length=32)
    model_id: str = Field(default="", max_length=256)
    category: str = Field(default="user_custom", max_length=64)
    category_label: str = Field(default="自定义", max_length=128)
    category_order: int = 500
    sort_order: int = 0
    scopes: list[str] = Field(default_factory=list)
    scope_summary: str = Field(default="", max_length=8000)
    canvas_node_kinds: list[str] = Field(default_factory=list)
    canvas_universal: bool = False
    api_kind: str = Field(default="ark_chat", max_length=32)
    show_in_canvas_llm_nodes: bool = True
    is_active: bool = True
    variants: list[dict[str, str]] = Field(default_factory=list, description="二级选项（如语音音色 variants）")


class AIModelVariantOutSchema(Schema):
    id: int
    model_entry_id: int
    kind: str
    variant_id: str
    label: str
    value: str
    sort_order: int
    config: dict = Field(default_factory=dict)
    is_active: bool


class AIModelVariantCreateSchema(Schema):
    kind: str = Field(default="voice", max_length=24)
    variant_id: str = Field(..., max_length=96)
    label: str = Field(default="", max_length=160)
    value: str = Field(default="", max_length=256)
    sort_order: int = 0
    config: dict = Field(default_factory=dict)
    is_active: bool = True


class AIModelVariantPatchSchema(Schema):
    kind: str | None = Field(default=None, max_length=24)
    variant_id: str | None = Field(default=None, max_length=96)
    label: str | None = Field(default=None, max_length=160)
    value: str | None = Field(default=None, max_length=256)
    sort_order: int | None = None
    config: dict | None = None
    is_active: bool | None = None


def _variant_to_out(v: AIModelVariant) -> AIModelVariantOutSchema:
    return AIModelVariantOutSchema(
        id=int(v.pk),
        model_entry_id=int(v.model_entry_id),
        kind=str(v.kind or ""),
        variant_id=str(v.variant_id or ""),
        label=str(v.label or ""),
        value=str(v.value or ""),
        sort_order=int(v.sort_order or 0),
        config=dict(v.config or {}),
        is_active=bool(v.is_active),
    )


class AIModelCatalogEntryPatchSchema(Schema):
    label: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=512)
    route: str | None = Field(default=None, max_length=32)
    model_id: str | None = Field(default=None, max_length=256)
    category: str | None = Field(default=None, max_length=64)
    category_label: str | None = Field(default=None, max_length=128)
    category_order: int | None = None
    sort_order: int | None = None
    scopes: list[str] | None = None
    scope_summary: str | None = Field(default=None, max_length=8000)
    canvas_node_kinds: list[str] | None = None
    canvas_universal: bool | None = None
    api_kind: str | None = Field(default=None, max_length=32)
    show_in_canvas_llm_nodes: bool | None = None
    is_active: bool | None = None


@ai_router.get("/models", response=AIModelsCatalogSchema)
def list_ai_models(request: HttpRequest):
    """
    GET /api/ai/models

    返回「项目内置 + 当前登录用户自定义」模型列表（无密钥）。
    未登录时仅返回内置项（``source=project``）。
    """
    user = getattr(request, "auth", None)
    rows = list_models_merged_for_api(user)
    return AIModelsCatalogSchema(models=[AIModelEntrySchema(**row) for row in rows])


@ai_router.get("/catalog-entries", response=list[AIModelCatalogEntryOutSchema])
def list_aimodel_catalog_entries(request: HttpRequest, active_only: bool = False):
    """
    GET /api/ai/catalog-entries

    管理员：列出数据库中的项目模型目录（含已停用项，便于后台维护）。
    """
    _require_staff(request)
    qs = AIModelCatalogEntry.objects.all().order_by("category_order", "sort_order", "catalog_key")
    if active_only:
        qs = qs.filter(is_active=True)
    return [_catalog_entry_to_out(x) for x in qs]


@ai_router.get("/catalog-entries/{entry_id}/variants", response=list[AIModelVariantOutSchema])
def list_catalog_entry_variants(request: HttpRequest, entry_id: int, active_only: bool = False):
    """GET /api/ai/catalog-entries/{id}/variants — 管理员：列出某个模型目录项的二级选项。"""
    _require_staff(request)
    qs = AIModelVariant.objects.filter(model_entry_id=int(entry_id)).order_by("sort_order", "id")
    if active_only:
        qs = qs.filter(is_active=True)
    return [_variant_to_out(v) for v in qs]


@ai_router.post("/catalog-entries/{entry_id}/variants", response={201: AIModelVariantOutSchema})
def create_catalog_entry_variant(request: HttpRequest, entry_id: int, payload: AIModelVariantCreateSchema):
    """POST /api/ai/catalog-entries/{id}/variants — 管理员新增二级选项。"""
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    _require_staff(request)
    vid = (payload.variant_id or "").strip()
    if not vid:
        raise HttpError(400, "variant_id 不能为空")
    obj = AIModelVariant.objects.create(
        model_entry_id=int(entry_id),
        kind=str(payload.kind or "voice"),
        variant_id=vid,
        label=str(payload.label or "").strip()[:160],
        value=str(payload.value or "").strip()[:256],
        sort_order=int(payload.sort_order or 0),
        config=dict(payload.config or {}),
        is_active=bool(payload.is_active),
    )
    return 201, _variant_to_out(obj)


@ai_router.patch("/catalog-entries/{entry_id}/variants/{variant_pk}", response=AIModelVariantOutSchema)
def patch_catalog_entry_variant(
    request: HttpRequest,
    entry_id: int,
    variant_pk: int,
    payload: AIModelVariantPatchSchema,
):
    """PATCH /api/ai/catalog-entries/{id}/variants/{pk} — 管理员更新二级选项。"""
    _require_staff(request)
    obj = get_object_or_404(AIModelVariant, pk=int(variant_pk), model_entry_id=int(entry_id))
    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        if val is None:
            continue
        if field == "sort_order":
            obj.sort_order = int(val)
            continue
        if field == "config":
            obj.config = dict(val or {})
            continue
        if field == "is_active":
            obj.is_active = bool(val)
            continue
        if field == "label":
            obj.label = str(val).strip()[:160]
            continue
        if field == "value":
            obj.value = str(val).strip()[:256]
            continue
        if field == "variant_id":
            obj.variant_id = str(val).strip()[:96]
            continue
        if field == "kind":
            obj.kind = str(val).strip()[:24]
            continue
    obj.save()
    return _variant_to_out(obj)


@ai_router.delete("/catalog-entries/{entry_id}/variants/{variant_pk}", response={204: None})
def delete_catalog_entry_variant(request: HttpRequest, entry_id: int, variant_pk: int):
    """DELETE /api/ai/catalog-entries/{id}/variants/{pk} — 管理员删除二级选项。"""
    _require_staff(request)
    AIModelVariant.objects.filter(pk=int(variant_pk), model_entry_id=int(entry_id)).delete()
    return 204, None


@ai_router.post("/catalog-entries", response={201: AIModelCatalogEntryOutSchema})
def create_aimodel_catalog_entry(request: HttpRequest, payload: AIModelCatalogEntryCreateSchema):
    """POST /api/ai/catalog-entries — 管理员新增目录项。"""
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    _require_staff(request)
    ck = (payload.catalog_key or "").strip()
    if AIModelCatalogEntry.objects.filter(catalog_key=ck).exists():
        raise HttpError(400, f"catalog_key 已存在: {ck}")
    kinds = {c.value for c in AIModelCatalogEntry.ApiKind}
    ak = (payload.api_kind or "").strip()
    if ak not in kinds:
        raise HttpError(400, f"api_kind 必须是: {', '.join(sorted(kinds))}")
    obj = AIModelCatalogEntry.objects.create(
        catalog_key=ck,
        label=(payload.label or "").strip(),
        description=(payload.description or "").strip()[:512],
        route=(payload.route or "doubao").strip()[:32],
        model_id=(payload.model_id or "").strip()[:256],
        category=(payload.category or "user_custom").strip()[:64],
        category_label=(payload.category_label or "自定义").strip()[:128],
        category_order=int(payload.category_order),
        sort_order=int(payload.sort_order),
        scopes=[str(x).strip() for x in (payload.scopes or []) if str(x).strip()],
        scope_summary=(payload.scope_summary or "").strip(),
        canvas_node_kinds=list(payload.canvas_node_kinds or []),
        canvas_universal=bool(payload.canvas_universal),
        api_kind=ak,
        show_in_canvas_llm_nodes=bool(payload.show_in_canvas_llm_nodes),
        is_active=bool(payload.is_active),
    )
    return 201, _catalog_entry_to_out(obj)


@ai_router.patch("/catalog-entries/{entry_id}", response=AIModelCatalogEntryOutSchema)
def patch_aimodel_catalog_entry(
    request: HttpRequest, entry_id: int, payload: AIModelCatalogEntryPatchSchema
):
    """PATCH /api/ai/catalog-entries/{id} — 管理员更新目录项。"""
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    _require_staff(request)
    obj = get_object_or_404(AIModelCatalogEntry, pk=entry_id)
    kinds = {c.value for c in AIModelCatalogEntry.ApiKind}
    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        if val is None:
            continue
        if field == "api_kind":
            if str(val) not in kinds:
                raise HttpError(400, f"api_kind 必须是: {', '.join(sorted(kinds))}")
            obj.api_kind = str(val)
            continue
        if field in ("category_order", "sort_order"):
            setattr(obj, field, int(val))
            continue
        if field == "scopes":
            obj.scopes = [str(x).strip() for x in val if str(x).strip()]
            continue
        if field == "canvas_node_kinds":
            obj.canvas_node_kinds = list(val or [])
            continue
        setattr(obj, field, val)
    obj.save()
    return _catalog_entry_to_out(obj)


@ai_router.delete("/catalog-entries/{entry_id}", response={200: dict})
def delete_aimodel_catalog_entry(request: HttpRequest, entry_id: int):
    """DELETE /api/ai/catalog-entries/{id} — 管理员删除目录项（硬删除）。"""
    _require_staff(request)
    obj = get_object_or_404(AIModelCatalogEntry, pk=entry_id)
    obj.delete()
    return 200, {"ok": True}


class PromptEnhanceInputSchema(Schema):
    workflow_id: int | None = None
    client_node_id: str = Field(default="", max_length=128)
    node_type: str = Field(default="", max_length=64)
    field: str = Field(..., min_length=1, max_length=64)
    raw_prompt: str = Field(..., min_length=1, max_length=20000)
    instruction: str = Field(default="", max_length=4000)
    model_key: str = Field(default="", max_length=64)
    provider_route: str = Field(default="", max_length=32)
    model: str = Field(default="", max_length=128)
    temperature: float | None = None
    max_tokens: int | None = None


class PromptEnhanceOutputSchema(Schema):
    record_id: int
    candidates: list[str]
    suggested: str
    used_provider_route: str
    used_model: str


@prompt_tools_router.post("/enhance", response=PromptEnhanceOutputSchema)
def enhance_prompt(request: HttpRequest, payload: PromptEnhanceInputSchema):
    """
    POST /api/prompt-tools/enhance

    基于用户输入生成 3 条“加工后的提示词”候选，并写入审计表。
    """
    current_user = request.auth
    if current_user is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")

    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    wf: Workflow | None = None
    if payload.workflow_id is not None:
        wf = Workflow.objects.filter(id=payload.workflow_id, user=current_user).first()

    raw = (payload.raw_prompt or "").strip()
    if not raw:
        raise HttpError(400, {"message": "raw_prompt 不能为空"})

    instruction = (payload.instruction or "").strip()
    mk = (payload.model_key or "").strip()
    cat_key = ""
    if mk:
        route, model_id, cat_key = resolve_route_and_model_id({"modelKey": mk}, user_id=current_user.pk)
    else:
        route = (payload.provider_route or "").strip().lower()
        if route in ("ark", "byte", "volcengine"):
            route = "doubao"
        model_id = (payload.model or "").strip()
        if not route:
            route, model_id, cat_key = resolve_route_and_model_id(
                {"modelKey": "doubao-default"}, user_id=current_user.pk
            )
        elif not model_id:
            model_id = _default_model_for_route(route)
    if not model_id:
        raise HttpError(400, {"message": "未能解析模型，请检查环境默认模型或显式传入 model"})

    llm_overrides = get_user_preset_llm_overrides(cat_key, current_user.pk)

    # Build model
    llm = get_chat_model(
        route,
        model=model_id,
        temperature=payload.temperature if payload.temperature is not None else 0.7,
        max_tokens=payload.max_tokens if payload.max_tokens is not None else 1024,
        streaming=False,
        **llm_overrides,
    )

    # Ask the model to output JSON array of 3 strings.
    sys = (
        "你是一个提示词工程助手。你的任务是将用户给定的提示词进行加工与优化，使其更清晰、可执行、约束明确。\n"
        "输出要求：只输出严格的 JSON 数组，数组长度为 3，每项是字符串，不要包含任何额外文字。"
    )
    user = (
        f"字段: {payload.field}\n"
        f"用户原文:\n{raw}\n\n"
        f"额外要求(可空):\n{instruction}\n\n"
        "请给出 3 个不同风格的改写版本：\n"
        "1) 简洁直接\n2) 结构化（分点/步骤）\n3) 强约束（明确输入/输出/边界）\n"
    )

    from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]

    resp = llm.invoke([SystemMessage(content=sys), HumanMessage(content=user)])
    text = getattr(resp, "content", str(resp))

    candidates: list[str] = []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            candidates = [str(x) for x in parsed if str(x).strip()]
    except Exception:
        candidates = []

    if not candidates:
        # Fallback: treat full text as one candidate
        candidates = [text.strip()]

    # Normalize to exactly 3 candidates if possible
    if len(candidates) > 3:
        candidates = candidates[:3]
    while len(candidates) < 3:
        candidates.append(candidates[-1])

    suggested = candidates[0]

    rec = PromptEnhancementRecord.objects.create(
        user=current_user,
        workflow=wf,
        client_node_id=payload.client_node_id or None,
        node_type=payload.node_type or None,
        field=payload.field,
        raw_prompt=raw,
        instruction=instruction or None,
        candidates=candidates,
        suggested_text=suggested,
        selected_text=None,
        provider_route=route,
        model=model_id,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    return PromptEnhanceOutputSchema(
        record_id=rec.id,
        candidates=candidates,
        suggested=suggested,
        used_provider_route=route,
        used_model=model_id,
    )


# ─── 用户自定义聊天模型预设（CRUD，modelKey 形如 user:<id>）──────────────────────


class UserChatModelPresetCreateSchema(Schema):
    display_name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="", max_length=4000)
    route: str = Field(..., min_length=1, max_length=32)
    model_id: str = Field(..., min_length=1, max_length=256)
    is_active: bool = Field(default=True)
    category: str = Field(default="user_custom", max_length=32)
    category_label: str = Field(default="我的模型", max_length=128)
    category_order: int = Field(default=100, ge=0, le=32767)
    scopes: list[str] = Field(default_factory=list)
    scope_summary: str = Field(default="", max_length=4000)
    api_key: str = Field(default="", max_length=4096)
    api_base_url: str = Field(default="", max_length=512)


class UserChatModelPresetUpdateSchema(Schema):
    display_name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=4000)
    route: str | None = Field(default=None, max_length=32)
    model_id: str | None = Field(default=None, max_length=256)
    is_active: bool | None = None
    category: str | None = Field(default=None, max_length=32)
    category_label: str | None = Field(default=None, max_length=128)
    category_order: int | None = Field(default=None, ge=0, le=32767)
    scopes: list[str] | None = None
    scope_summary: str | None = Field(default=None, max_length=4000)
    api_key: str | None = Field(default=None, max_length=4096)
    api_base_url: str | None = Field(default=None, max_length=512)


class UserChatModelPresetOutSchema(Schema):
    id: int
    key: str
    display_name: str
    description: str
    route: str
    model_id: str
    is_active: bool
    category: str
    category_label: str
    category_order: int
    scopes: list[str]
    scope_summary: str
    has_custom_credentials: bool


def _user_route_allowed(route: str) -> str:
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    r = (route or "").strip().lower()
    allowed = {c.value for c in UserChatModelPreset.ProviderRoute}
    if r not in allowed:
        raise HttpError(400, {"message": f"route 必须是: {', '.join(sorted(allowed))}"})
    return r


def _user_preset_to_out(o: UserChatModelPreset) -> UserChatModelPresetOutSchema:
    return UserChatModelPresetOutSchema(
        id=o.pk,
        key=o.api_model_key,
        display_name=o.display_name,
        description=o.description or "",
        route=o.route,
        model_id=o.model_id,
        is_active=o.is_active,
        category=o.category,
        category_label=o.category_label,
        category_order=o.category_order,
        scopes=list(o.scopes or []),
        scope_summary=o.scope_summary or "",
        has_custom_credentials=bool((o.api_key_encrypted or "").strip()),
    )


@ai_router.get("/user-chat-model-presets", response=list[UserChatModelPresetOutSchema])
def list_user_chat_model_presets(request: HttpRequest):
    """GET /api/ai/user-chat-model-presets — 列出当前用户全部自定义（含已停用）。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    qs = UserChatModelPreset.objects.filter(user=u).order_by("-updated_at")
    return [_user_preset_to_out(x) for x in qs]


@ai_router.post("/user-chat-model-presets", response={201: UserChatModelPresetOutSchema})
def create_user_chat_model_preset(request: HttpRequest, payload: UserChatModelPresetCreateSchema):
    """POST /api/ai/user-chat-model-presets — 新增自定义模型（写入后 modelKey = 响应中的 key）。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    rid = _user_route_allowed(payload.route)
    mid = (payload.model_id or "").strip()
    if not mid:
        raise HttpError(400, {"message": "model_id 不能为空"})
    obj = UserChatModelPreset.objects.create(
        user=u,
        display_name=(payload.display_name or "").strip(),
        description=(payload.description or "").strip(),
        route=rid,
        model_id=mid,
        is_active=bool(payload.is_active),
        category=(payload.category or "user_custom").strip() or "user_custom",
        category_label=(payload.category_label or "我的模型").strip() or "我的模型",
        category_order=int(payload.category_order),
        scopes=[str(x).strip() for x in (payload.scopes or []) if str(x).strip()],
        scope_summary=(payload.scope_summary or "").strip(),
        api_base_url=(payload.api_base_url or "").strip()[:512],
    )
    obj.set_api_key((payload.api_key or "").strip() or None)
    obj.save()
    return 201, _user_preset_to_out(obj)


@ai_router.patch("/user-chat-model-presets/{preset_id}", response=UserChatModelPresetOutSchema)
def patch_user_chat_model_preset(
    request: HttpRequest, preset_id: int, payload: UserChatModelPresetUpdateSchema
):
    """PATCH /api/ai/user-chat-model-presets/{id} — 修改名称、route、model_id、启用状态等。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    obj = get_object_or_404(UserChatModelPreset, pk=preset_id, user=u)
    if payload.display_name is not None:
        obj.display_name = (payload.display_name or "").strip()
    if payload.description is not None:
        obj.description = (payload.description or "").strip()
    if payload.route is not None:
        obj.route = _user_route_allowed(payload.route)
    if payload.model_id is not None:
        t = (payload.model_id or "").strip()
        if not t:
            raise HttpError(400, {"message": "model_id 不能为空"})
        obj.model_id = t
    if payload.is_active is not None:
        obj.is_active = bool(payload.is_active)
    if payload.category is not None:
        obj.category = (payload.category or "").strip() or "user_custom"
    if payload.category_label is not None:
        obj.category_label = (payload.category_label or "").strip() or "我的模型"
    if payload.category_order is not None:
        obj.category_order = int(payload.category_order)
    if payload.scopes is not None:
        obj.scopes = [str(x).strip() for x in payload.scopes if str(x).strip()]
    if payload.scope_summary is not None:
        obj.scope_summary = (payload.scope_summary or "").strip()
    if payload.api_base_url is not None:
        obj.api_base_url = (payload.api_base_url or "").strip()[:512]
    if payload.api_key is not None:
        obj.set_api_key(payload.api_key)
    obj.save()
    return _user_preset_to_out(obj)


@ai_router.delete("/user-chat-model-presets/{preset_id}", response={200: dict})
def delete_user_chat_model_preset(request: HttpRequest, preset_id: int):
    """DELETE /api/ai/user-chat-model-presets/{id} — 删除自定义模型。"""
    u = request.auth
    if u is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")
    obj = get_object_or_404(UserChatModelPreset, pk=preset_id, user=u)
    obj.delete()
    return 200, {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# 工作流编辑页「引导助手」：独立系统提示词 + 每工作流一份 Markdown 说明
# ─────────────────────────────────────────────────────────────────────────────

WORKFLOW_GUIDE_SYSTEM_PROMPT = """你是 Flowly 工作流编辑与运行专家助手。

你的职责
- 帮助用户理解、设计与调试画布工作流：节点类型、连线（edges）、输入输出衔接、保存与校验错误。
- 解释「画布运行」与 LangGraph 式工作流的差异时，以当前产品能力为准，避免臆造不存在的功能。
- 回答应简洁、可执行；需要时给出分步骤建议或检查清单。

约束
- 不要编造用户工作流中不存在的节点或配置；若缺少上下文，先说明假设再建议。
- 不要输出任何密钥、token、环境变量值或内部文件路径（除用户已知的公开配置名）。
- 若用户要求「更新工作流说明文档」的内容，在回复中用 Markdown 给出建议段落，并说明可粘贴到说明文件中；除非系统另行开放写接口，不要声称已自动写入服务器文件。
"""


def _workflow_guide_doc_path(workflow_id: int) -> Path:
    root = Path(getattr(settings, "MEDIA_ROOT", "") or "") / "workflow_guides"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{workflow_id}.md"


def _render_initial_workflow_guide_markdown(wf: Workflow) -> str:
    name = (wf.name or "").strip() or "（未命名）"
    desc = (wf.description or "").strip() or "（暂无描述，可在编辑器中补充。）"
    definition = wf.definition if isinstance(wf.definition, dict) else {}
    nodes = definition.get("nodes") if isinstance(definition.get("nodes"), list) else []
    edges = definition.get("edges") if isinstance(definition.get("edges"), list) else []

    lines: list[str] = [
        f"# 工作流「{name}」说明",
        "",
        "## 概述",
        desc,
        "",
        "## 节点一览",
    ]
    if not nodes:
        lines.append("（当前尚无节点）")
    else:
        for n in nodes[:80]:
            if not isinstance(n, dict):
                continue
            nid = str(n.get("id", "")).strip() or "?"
            nt = str(n.get("type", "")).strip() or "?"
            lab = str(n.get("label", "")).strip()
            tail = f" — {lab}" if lab else ""
            lines.append(f"- `{nid}` — 类型 `{nt}`{tail}")

    lines.extend(["", "## 连线"])
    if not edges:
        lines.append("（当前尚无连线）")
    else:
        for e in edges[:120]:
            if not isinstance(e, dict):
                continue
            s = str(e.get("source", "")).strip()
            t = str(e.get("target", "")).strip()
            lines.append(f"- `{s}` → `{t}`")

    lines.extend(
        [
            "",
            "## 维护说明",
            "本文件由系统在首次打开「工作流助手」时根据画布定义自动生成。"
            "你可以在后续对话中请助手帮你改写本节，再将助手给出的 Markdown 粘贴保存到本说明思路中（或联系产品后续支持服务端写入）。",
            "",
        ]
    )
    return "\n".join(lines)


def _load_or_create_workflow_guide_markdown(wf: Workflow) -> str:
    path = _workflow_guide_doc_path(int(wf.id))
    if path.is_file() and path.stat().st_size > 0:
        return path.read_text(encoding="utf-8", errors="replace")
    body = _render_initial_workflow_guide_markdown(wf)
    path.write_text(body, encoding="utf-8")
    return body


def _default_model_for_route(route: str) -> str:
    s = get_ai_provider_settings()
    r = (route or "").strip().lower()
    if r in ("ark", "byte", "volcengine"):
        r = "doubao"
    mapping = {
        "openai": s.language.openai_model,
        "claude": s.language.anthropic_model,
        "ollama": s.language.ollama_model,
        "vectorengine": s.language.vectorengine_model,
        "doubao": s.language.doubao_ark_model,
    }
    return (mapping.get(r) or s.language.openai_model or "").strip()


class WorkflowGuideChatMessageSchema(Schema):
    role: str = Field(..., min_length=1, max_length=16)
    content: str = Field(..., min_length=1, max_length=20000)


class WorkflowGuideChatInputSchema(Schema):
    messages: list[WorkflowGuideChatMessageSchema] = Field(default_factory=list)
    model_key: str = Field(default="", max_length=64)
    provider_route: str = Field(default="", max_length=32)
    model: str = Field(default="", max_length=128)
    workflow_id: int | None = None


class WorkflowGuideChatOutputSchema(Schema):
    reply: str
    used_provider: str
    used_model: str


@ai_router.post("/workflow-guide/chat", response=WorkflowGuideChatOutputSchema)
def workflow_guide_chat(request: HttpRequest, payload: WorkflowGuideChatInputSchema):
    """
    POST /api/ai/workflow-guide/chat

    面向工作流编辑页的专用对话：固定系统提示词，并在存在 workflow_id 时
    注入 ``MEDIA_ROOT/workflow_guides/<id>.md``（不存在则根据 definition 生成）。
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]
    from ninja.errors import AuthenticationError, HttpError  # pyright: ignore[reportMissingImports]

    current_user = request.auth
    if current_user is None:
        raise AuthenticationError("Authentication required")

    msgs_in = payload.messages or []
    if not msgs_in:
        raise HttpError(400, {"message": "messages 不能为空"})

    guide_text = ""
    wf: Workflow | None = None
    if payload.workflow_id is not None:
        wf = Workflow.objects.filter(id=payload.workflow_id, user=current_user).first()
        if wf is None:
            raise HttpError(404, {"message": "工作流不存在或无权访问"})
        guide_text = _load_or_create_workflow_guide_markdown(wf)

    mk = (payload.model_key or "").strip()
    cat_key = ""
    if mk:
        route, model_id, cat_key = resolve_route_and_model_id({"modelKey": mk}, user_id=current_user.pk)
    else:
        route = (payload.provider_route or "").strip().lower()
        if route in ("ark", "byte", "volcengine"):
            route = "doubao"
        model_id = (payload.model or "").strip()
        if not route:
            route, model_id, cat_key = resolve_route_and_model_id(
                {"modelKey": "doubao-default"}, user_id=current_user.pk
            )
        elif not model_id:
            model_id = _default_model_for_route(route)
    if not model_id:
        raise HttpError(400, {"message": "未能解析默认模型，请传入 model_key 或 model"})

    llm_overrides = get_user_preset_llm_overrides(cat_key, current_user.pk)

    lc_messages: list[Any] = []
    for m in msgs_in[-40:]:
        role = (m.role or "").strip().lower()
        content = (m.content or "").strip()
        if not content:
            continue
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    if not lc_messages:
        raise HttpError(400, {"message": "messages 中需至少一条有效的 user/assistant 内容"})

    doc_section = (
        "\n\n【工作流说明文件（Markdown）】\n"
        + guide_text
        if guide_text
        else "\n\n【工作流说明文件】\n（当前为未保存工作流或未关联 workflow_id，无说明文件。请基于通用工作流编辑实践回答。）"
    )
    system = WORKFLOW_GUIDE_SYSTEM_PROMPT + doc_section
    full = [SystemMessage(content=system), *lc_messages]

    try:
        llm = get_chat_model(
            route,
            model=model_id,
            temperature=0.6,
            max_tokens=2048,
            streaming=False,
            **llm_overrides,
        )
        resp = llm.invoke(full)
    except ValueError as e:
        raise HttpError(400, {"message": str(e)}) from e
    except Exception as e:  # noqa: BLE001 — 统一为可读错误
        raise HttpError(502, {"message": f"模型调用失败: {e!s}"}) from e

    reply = getattr(resp, "content", None)
    if reply is None:
        reply = str(resp)
    reply = str(reply).strip()
    if not reply:
        reply = "（模型未返回有效文本，请重试或更换模型。）"

    return WorkflowGuideChatOutputSchema(
        reply=reply,
        used_provider=route,
        used_model=model_id,
    )

