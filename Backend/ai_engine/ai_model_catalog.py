"""
AI 聊天模型解析与列表：

1. **项目内置预设**（``CHAT_MODEL_PRESETS``）：``category`` / ``category_label`` 按 **功能场景**
   （如默认画布、多模态理解、复杂推理、高频轻量等）划分，**不按厂商**；``route`` 仍表示底层接入线路。
2. **用户自定义预设**（``UserChatModelPreset``）：``modelKey`` = ``user:<id>``；可填写自有
   ``api_key`` / ``api_base_url``（库内加密存储），调用时通过 ``get_chat_model`` 的 override 注入。

旧版 ``provider`` + ``model`` 仍兼容。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ai_engine.integrations import get_ai_provider_settings


# 画布带「模型」下拉的节点类型（与 WorkflowEditor inspector 一致）
CANVAS_LLM_NODE_KINDS: tuple[str, ...] = ("chat", "text", "image", "audio", "video")


@dataclass(frozen=True, slots=True)
class ChatModelPreset:
    key: str
    label: str
    description: str
    route: str
    # 空字符串表示该线路使用环境变量中的默认 model
    model_id: str
    # 功能场景分类（稳定 id，供前端分组 / 排序；与厂商无关）
    category: str
    category_label: str
    category_order: int
    # 简短标签：适用哪些画布能力
    scopes: tuple[str, ...]
    # 一段话说明「可用来做什么」
    scope_summary: str
    # 仅在这些画布节点类型的下拉中出现；空元组表示不限制（所有带模型的节点）
    canvas_node_kinds: tuple[str, ...] = ()
    # 为 True 时忽略 canvas_node_kinds，在所有带模型节点中可选（如豆包智能路由）
    canvas_universal: bool = False


_ALL_LLM_NODES: tuple[str, ...] = CANVAS_LLM_NODE_KINDS
_NO_IMAGE: tuple[str, ...] = ("chat", "text", "audio", "video")


CHAT_MODEL_PRESETS: tuple[ChatModelPreset, ...] = (
    ChatModelPreset(
        "doubao-default",
        "豆包（项目默认）",
        "使用环境变量中的方舟接入点（DOUBAO_ARK_MODEL 等）",
        "doubao",
        "",
        "fn_canvas_default",
        "画布默认 · 对话与多模态理解",
        0,
        ("对话节点", "文本处理", "看图说话", "听写后摘要", "视频说明摘要"),
        "推荐作为画布首选：中文对话、模板文本、看图/听转写/视频说明类节点。说明：输出为文本；"
        "「文生图像素图」需专用绘图服务，本模型可承担配图思路、绘图提示词（如 SD/MJ 英文 prompt）与画面描述。",
        canvas_node_kinds=_ALL_LLM_NODES,
    ),
    ChatModelPreset(
        "openai-default",
        "OpenAI（项目默认）",
        "使用环境变量中的 OpenAI 默认模型与密钥",
        "openai",
        "",
        "fn_general_assistant",
        "通用助手 · 对话与提示词加工",
        10,
        ("工作流助手", "提示词加工", "中英混排", "简单分析"),
        "适合作为「通用第二选择」：与画布编辑器里的 AI 加工、助手类功能搭配；偏均衡的中等复杂度任务。",
        canvas_node_kinds=_ALL_LLM_NODES,
    ),
    ChatModelPreset(
        "openai-gpt-4o",
        "OpenAI · GPT-4o",
        "固定使用 gpt-4o",
        "openai",
        "gpt-4o",
        "fn_creative_visual",
        "视觉创意 · 绘图提示与高质量推理",
        20,
        ("文生图/图生图提示词", "分镜与画面描述", "复杂推理", "结构化输出", "看图问答（若网关支持）"),
        "适合需要「把想法变成可执行的绘图 prompt、分镜、镜头表」以及高复杂度推理的节点。"
        "说明：此处仍是语言模型，不直接输出像素图；出图请接专用文生图服务，本模型负责提示词与创意文案。",
        canvas_node_kinds=_ALL_LLM_NODES,
    ),
    ChatModelPreset(
        "openai-gpt-4o-mini",
        "OpenAI · GPT-4o mini",
        "固定使用 gpt-4o-mini",
        "openai",
        "gpt-4o-mini",
        "fn_high_volume",
        "高频轻量 · 省钱省时",
        30,
        ("大量摘要", "标签分类", "初稿扩写", "预演打样"),
        "适合大批量、低单价节点：快速分类、短摘要、占位文案；不适合强推理或长链依赖。",
        canvas_node_kinds=_NO_IMAGE,
    ),
    ChatModelPreset(
        "openai-gpt-4-turbo",
        "OpenAI · GPT-4 Turbo",
        "固定使用 gpt-4-turbo",
        "openai",
        "gpt-4-turbo",
        "fn_longform_code",
        "长文梳理 · 代码与工具型",
        25,
        ("长文总结", "代码解释", "接口说明草稿", "表格化输出"),
        "偏长上下文与代码/技术说明；适合「把长材料收成要点」或生成接口/配置说明类文本。",
        canvas_node_kinds=_ALL_LLM_NODES,
    ),
    ChatModelPreset(
        "openai-gpt-3-5-turbo",
        "OpenAI · GPT-3.5 Turbo",
        "固定使用 gpt-3.5-turbo",
        "openai",
        "gpt-3-5-turbo",
        "fn_high_volume",
        "高频轻量 · 省钱省时",
        30,
        ("轻量对话", "格式转换", "简单模板填充"),
        "与 mini 同属「高频低成本」档：延迟低、适合简单变换与试错；复杂逻辑请换高质量档。",
        canvas_node_kinds=_NO_IMAGE,
    ),
    ChatModelPreset(
        "claude-default",
        "Claude（项目默认）",
        "使用环境变量中的 Anthropic 默认模型",
        "claude",
        "",
        "fn_reading_writing",
        "深度阅读 · 长文写作",
        35,
        ("长文精读", "报告写作", "条款润色", "多轮修订"),
        "适合长文档阅读、写作与反复打磨类节点；需项目已配置 Anthropic 密钥。",
        canvas_node_kinds=_ALL_LLM_NODES,
    ),
    ChatModelPreset(
        "ollama-default",
        "Ollama（项目默认）",
        "使用环境变量中的 Ollama 模型与地址",
        "ollama",
        "",
        "fn_private_local",
        "私有化 · 离线/内网试验",
        40,
        ("内网 PoC", "数据不出域", "本地调参"),
        "数据留在自有机器或内网；适合对公网出域敏感的环境，能力取决于所装本地模型。",
        canvas_node_kinds=_ALL_LLM_NODES,
    ),
    ChatModelPreset(
        "vectorengine-default",
        "VectorEngine（项目默认）",
        "使用环境变量中的 VectorEngine 模型",
        "vectorengine",
        "",
        "fn_compliance_route",
        "合规线路 · 企业代理网关",
        45,
        ("走企业代理", "统一审计出口", "兼容 OpenAI 调用形态"),
        "适合必须走指定合规出口、由企业网关转发的场景；具体模型名与配额以网关配置为准。",
        canvas_node_kinds=_ALL_LLM_NODES,
    ),
)

_BY_KEY: dict[str, ChatModelPreset] = {p.key: p for p in CHAT_MODEL_PRESETS}

_BY_MODEL_ID: dict[str, ChatModelPreset] = {
    p.model_id: p for p in CHAT_MODEL_PRESETS if (p.model_id or "").strip()
}


def _preset_to_api_row(p: ChatModelPreset, *, source: str) -> dict[str, Any]:
    # 简单从 canvas_node_kinds 推断可发送的模态
    kinds = set(p.canvas_node_kinds or ())
    modalities = ["text"]
    if "image" in kinds:
        modalities.append("image")
    if "audio" in kinds:
        modalities.append("audio")
    if "video" in kinds:
        modalities.append("video")
    return {
        "key": p.key,
        "label": p.label,
        "description": p.description,
        "route": p.route,
        "modalities": modalities,
        "source": source,
        "category": p.category,
        "category_label": p.category_label,
        "category_order": p.category_order,
        "scopes": list(p.scopes),
        "scope_summary": p.scope_summary,
        "has_custom_credentials": False,
        "canvas_node_kinds": list(p.canvas_node_kinds),
        "canvas_universal": bool(p.canvas_universal),
        "api_kind": "ark_chat",
        "show_in_canvas_llm_nodes": True,
    }


def _db_entry_to_api_row(entry: Any, *, source: str = "catalog") -> dict[str, Any]:
    """``entry`` 为 ``AIModelCatalogEntry`` ORM 实例。"""
    kinds = set(entry.canvas_node_kinds or [])
    modalities = ["text"]
    if "image" in kinds:
        modalities.append("image")
    if "audio" in kinds:
        modalities.append("audio")
    if "video" in kinds:
        modalities.append("video")
    return {
        "key": entry.catalog_key,
        "label": entry.label,
        "description": (entry.description or "").strip(),
        "route": entry.normalized_route(),
        "modalities": modalities,
        "source": source,
        "category": entry.category,
        "category_label": entry.category_label,
        "category_order": int(entry.category_order or 0),
        "scopes": list(entry.scopes or []),
        "scope_summary": (entry.scope_summary or "").strip(),
        "has_custom_credentials": False,
        "canvas_node_kinds": list(entry.canvas_node_kinds or []),
        "canvas_universal": bool(entry.canvas_universal),
        "api_kind": str(entry.api_kind or "ark_chat"),
        "show_in_canvas_llm_nodes": bool(entry.show_in_canvas_llm_nodes),
    }


def list_presets_for_api() -> list[dict[str, str]]:
    """仅项目内置（扁平字段，兼容旧测试）：不含 scopes 等扩展字段。"""
    return [
        {"key": p.key, "label": p.label, "description": p.description, "route": p.route}
        for p in CHAT_MODEL_PRESETS
    ]


def list_models_merged_for_api(user: Any | None) -> list[dict[str, Any]]:
    """
    合并「数据库目录 + 代码内置预设（去重）+ 当前用户启用的自定义」，供 ``GET /api/ai/models``。
    """
    from ai_engine.models import AIModelCatalogEntry

    out: list[dict[str, Any]] = []
    db_keys: set[str] = set()
    for entry in AIModelCatalogEntry.objects.filter(is_active=True).order_by(
        "category_order", "sort_order", "catalog_key"
    ):
        out.append(_db_entry_to_api_row(entry, source="catalog"))
        db_keys.add(entry.catalog_key)

    for p in CHAT_MODEL_PRESETS:
        if p.key in db_keys:
            continue
        out.append(_preset_to_api_row(p, source="project"))

    if user is not None and getattr(user, "is_authenticated", False):
        from ai_engine.models import UserChatModelPreset

        for row in UserChatModelPreset.objects.filter(user=user, is_active=True).order_by("-updated_at"):
            kinds = set(CANVAS_LLM_NODE_KINDS)
            modalities = ["text"]
            if "image" in kinds:
                modalities.append("image")
            if "audio" in kinds:
                modalities.append("audio")
            if "video" in kinds:
                modalities.append("video")
            out.append(
                {
                    "key": row.api_model_key,
                    "label": row.display_name,
                    "description": (row.description or "").strip() or "用户自定义模型",
                    "route": row.normalized_route(),
                    "modalities": modalities,
                    "source": "user",
                    "category": row.category,
                    "category_label": row.category_label,
                    "category_order": row.category_order,
                    "scopes": list(row.scopes or []),
                    "scope_summary": (row.scope_summary or "").strip()
                    or "用户自行配置路由、模型 ID 与（可选）密钥；仅本人画布与工具可用。",
                    "has_custom_credentials": bool((row.api_key_encrypted or "").strip()),
                    "canvas_node_kinds": list(CANVAS_LLM_NODE_KINDS),
                    "canvas_universal": False,
                    "api_kind": "ark_chat",
                    "show_in_canvas_llm_nodes": True,
                }
            )
    out.sort(key=lambda r: (int(r.get("category_order") or 0), str(r.get("category") or ""), str(r.get("key") or "")))
    return out


def get_user_preset_llm_overrides(catalog_key: str, user_id: int | None) -> dict[str, Any]:
    """
    若 ``catalog_key`` 为用户预设且配置了自有密钥/地址，返回传给 ``get_chat_model`` 的覆盖参数。
    """
    if not catalog_key.startswith("user:") or not user_id:
        return {}
    tail = catalog_key[5:].strip()
    if not tail.isdigit():
        return {}
    from ai_engine.models import UserChatModelPreset

    row = UserChatModelPreset.objects.filter(pk=int(tail), user_id=user_id, is_active=True).first()
    if row is None:
        return {}
    extra: dict[str, Any] = {}
    key = row.get_api_key()
    if key:
        extra["api_key"] = key
    base = (row.api_base_url or "").strip()
    if base:
        extra["base_url"] = base
    return extra


def _resolve_user_catalog_key(catalog_key: str, user_id: int) -> tuple[str, str, str] | None:
    if not catalog_key.startswith("user:"):
        return None
    tail = catalog_key[5:].strip()
    if not tail.isdigit():
        return None
    from ai_engine.models import UserChatModelPreset

    row = UserChatModelPreset.objects.filter(pk=int(tail), user_id=user_id, is_active=True).first()
    if row is None:
        return None
    route = row.normalized_route()
    mid = (row.model_id or "").strip()
    if not mid:
        return None
    route, mid = _adjust_route_by_model_id(route, mid, route)
    return route, mid, catalog_key


def preset_label(key: str) -> str:
    from ai_engine.models import AIModelCatalogEntry

    e = AIModelCatalogEntry.objects.filter(catalog_key=key, is_active=True).first()
    if e is not None:
        return e.label
    p = _BY_KEY.get(key)
    return p.label if p else key


def _env_default_for_route(route: str, s: Any) -> str:
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
    return (mapping.get(r) or "").strip()


def _adjust_route_by_model_id(route: str, model_id: str, prov: str) -> tuple[str, str]:
    mlow = model_id.lower()
    if model_id and str(model_id).startswith("ep-"):
        route = "doubao"
    elif "doubao" in mlow and model_id:
        route = "doubao"
    elif "claude" in mlow or mlow.startswith("claude"):
        route = "claude"
    elif prov in ("ollama", "ollama_chat"):
        route = "ollama"
    elif prov == "vectorengine":
        route = "vectorengine"
    return route, model_id


def _finalize_doubao_model_for_ark_endpoint(route: str, model_id: str, s: Any) -> str:
    """
    火山方舟常见部署方式：控制台只下发 ``ep-`` 推理接入点，此时 OpenAI 兼容接口的 ``model``
    字段应填接入点 id；若仍传 ``Doubao-Seed-2.0-mini`` 等逻辑名会返回 InvalidEndpointOrModel。

    当环境 ``DOUBAO_ARK_MODEL`` 为 ``ep-…`` 时，将其它非 ep 的豆包模型名映射到该接入点。

    注意：部分账号/地域下 **不具备** ``Doubao-Smart-Router`` 的调用权限；此时传该模型名会 404。
    为了让默认配置更稳健，这里也把 ``Doubao-Smart-Router`` 映射到接入点（如需强制用 Smart-Router，
    请直接把 DOUBAO_ARK_MODEL 配置为该模型名，或在模型目录里填入可用的 endpoint/model）。
    """
    if (route or "").strip().lower() not in ("doubao", "ark", "byte", "volcengine"):
        return (model_id or "").strip()
    cfg = (s.language.doubao_ark_model or "").strip()
    if not cfg.startswith("ep-"):
        return (model_id or "").strip()
    mid = (model_id or "").strip()
    if mid.startswith("ep-"):
        return mid
    # 若传 Smart-Router 模型名，优先使用专用接入点（若配置）
    if mid.lower() == "doubao-smart-router":
        sr = (getattr(getattr(s, "language", None), "doubao_ark_smart_router_endpoint", "") or "").strip()
        if sr.startswith("ep-"):
            return sr
    return cfg


def resolve_route_and_model_id(
    config: Mapping[str, Any],
    *,
    user_id: int | None = None,
) -> tuple[str, str, str]:
    """
    解析 ``get_chat_model`` 所需的 route、model_id 与原始 ``catalog_key``（``user:`` 或内置 key）。
    """
    s = get_ai_provider_settings()
    catalog_key = str(config.get("modelKey") or config.get("model_key") or "").strip()
    explicit = str(config.get("model") or "").strip()
    prov = str(config.get("provider") or "doubao").strip().lower()
    if prov in ("ark", "byte", "volcengine"):
        prov = "doubao"

    uid: int | None = user_id
    if uid is None:
        ru = config.get("_runtime_user_id")
        if ru is not None and str(ru).strip().isdigit():
            uid = int(str(ru).strip())

    if catalog_key.startswith("user:"):
        if uid is None:
            raise ValueError(
                '自定义模型键以 "user:" 开头，需要已登录用户上下文（画布请使用登录用户运行）。'
            )
        resolved = _resolve_user_catalog_key(catalog_key, uid)
        if resolved is None:
            raise ValueError(f"自定义模型不存在、已停用或无权访问: {catalog_key}")
        r, m, k = resolved
        m = _finalize_doubao_model_for_ark_endpoint(r, m, s)
        return r, m, k

    if catalog_key:
        from ai_engine.models import AIModelCatalogEntry

        entry = AIModelCatalogEntry.objects.filter(catalog_key=catalog_key, is_active=True).first()
        if entry is not None:
            if str(entry.api_kind or "") != AIModelCatalogEntry.ApiKind.ARK_CHAT:
                raise ValueError(
                    f"模型「{entry.label}」为专用能力（api_kind={entry.api_kind}），"
                    "不能作为画布 LLM 节点的 modelKey；请选用方舟对话类（ark_chat）模型。"
                )
            route = entry.normalized_route()
            if route not in ("doubao", "openai", "claude", "ollama", "vectorengine"):
                raise ValueError(f"模型「{entry.label}」路由 {route} 暂不支持画布 LLM 调用。")
            mid = (entry.model_id or "").strip()
            if not mid:
                mid = _env_default_for_route(route, s)
            route, mid = _adjust_route_by_model_id(route, mid, prov)
            mid = _finalize_doubao_model_for_ark_endpoint(route, mid, s)
            return route, mid, catalog_key

    preset: ChatModelPreset | None = _BY_KEY.get(catalog_key) if catalog_key else None
    out_catalog_key = catalog_key
    if preset is None and catalog_key:
        by_model_alias = _BY_MODEL_ID.get(catalog_key)
        if by_model_alias is not None:
            preset = by_model_alias
            out_catalog_key = by_model_alias.key
    if preset is None and explicit in _BY_KEY:
        preset = _BY_KEY[explicit]
        out_catalog_key = preset.key
        explicit = ""

    if preset is not None:
        route = preset.route
        mid = (preset.model_id or "").strip()
        if not mid:
            mid = _env_default_for_route(route, s)
        route, mid = _adjust_route_by_model_id(route, mid, prov)
        mid = _finalize_doubao_model_for_ark_endpoint(route, mid, s)
        return route, mid, out_catalog_key

    alt = _BY_MODEL_ID.get(explicit)
    if alt is not None:
        route = alt.route
        mid = (alt.model_id or "").strip() or _env_default_for_route(route, s)
        route, mid = _adjust_route_by_model_id(route, mid, prov)
        mid = _finalize_doubao_model_for_ark_endpoint(route, mid, s)
        return route, mid, alt.key

    if explicit:
        from ai_engine.models import AIModelCatalogEntry

        entry = AIModelCatalogEntry.objects.filter(
            model_id=explicit,
            is_active=True,
            api_kind=AIModelCatalogEntry.ApiKind.ARK_CHAT,
        ).first()
        if entry is not None:
            route = entry.normalized_route()
            mid = (entry.model_id or "").strip() or _env_default_for_route(route, s)
            route, mid = _adjust_route_by_model_id(route, mid, prov)
            mid = _finalize_doubao_model_for_ark_endpoint(route, mid, s)
            return route, mid, entry.catalog_key

    route = "doubao"
    if prov in ("doubao", "ark", "volcengine", "byte"):
        route = "doubao"
    elif prov == "openai":
        route = "openai"
    elif prov == "claude":
        route = "claude"
    elif prov in ("ollama", "ollama_chat"):
        route = "ollama"
    elif prov == "vectorengine":
        route = "vectorengine"

    configured_doubao = (s.language.doubao_ark_model or "").strip()
    if explicit:
        model_id = explicit
    elif route == "doubao":
        model_id = configured_doubao
    else:
        model_id = ""

    route, model_id = _adjust_route_by_model_id(route, model_id, prov)
    model_id = _finalize_doubao_model_for_ark_endpoint(route, model_id, s)
    return route, model_id, ""
