"""
Execution History API — list, retrieve, statistics.

All endpoints require JWT authentication via HttpBearer.
"""

from io import BytesIO

from django.db.models import Count, Q
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .execution_artifacts import (
    build_docx_bytes,
    collect_media_artifacts,
    extract_primary_article_text,
)
from .execution_media_services import (
    convert_image_bytes,
    fetch_url_bytes,
    openai_text_to_image_bytes,
    openai_tts_bytes,
)
from .models import Workflow, WorkflowExecution, Thread

exec_router = Router(tags=["Executions"], auth=JWTAuth())


class ExecutionResponseSchema(Schema):
    id: int
    workflow_id: int
    workflow_name: str
    thread_id: str
    status: str
    input_data: dict
    output_data: dict
    error_message: str
    started_at: str
    completed_at: str | None
    duration_seconds: float | None = None


class ExecutionListSchema(Schema):
    total: int
    items: list[ExecutionResponseSchema]


class ExecutionStatsSchema(Schema):
    total_executions: int
    completed: int
    running: int
    pending: int
    failed: int
    avg_duration_seconds: float | None


class MessageSchema(Schema):
    message: str
    detail: str | None = None


def _execution_to_response(exec: WorkflowExecution) -> ExecutionResponseSchema:
    """Convert WorkflowExecution model to response schema."""
    duration = None
    if exec.started_at and exec.completed_at:
        delta = exec.completed_at - exec.started_at
        duration = delta.total_seconds()

    return ExecutionResponseSchema(
        id=exec.id,
        workflow_id=exec.workflow_id,
        workflow_name=exec.workflow.name if exec.workflow else "Unknown",
        thread_id=str(exec.thread.thread_id) if exec.thread else "",
        status=exec.status,
        input_data=exec.input_data or {},
        output_data=exec.output_data or {},
        error_message=exec.error_message or "",
        started_at=exec.started_at.isoformat() if exec.started_at else "",
        completed_at=exec.completed_at.isoformat() if exec.completed_at else None,
        duration_seconds=round(duration, 2) if duration is not None else None,
    )


@exec_router.get("/", response=ExecutionListSchema)
def list_executions(
    request: HttpRequest,
    workflow_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    GET /api/executions/

    List workflow executions for the authenticated user.
    """
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    queryset = WorkflowExecution.objects.filter(thread__user=u).select_related("workflow", "thread")

    if workflow_id is not None:
        queryset = queryset.filter(workflow_id=workflow_id)

    if status:
        queryset = queryset.filter(status=status)

    total = queryset.count()
    items = [
        _execution_to_response(e)
        for e in queryset.order_by("-started_at")[offset:offset + limit]
    ]

    return ExecutionListSchema(total=total, items=items)


@exec_router.get("/stats", response=ExecutionStatsSchema)
def execution_stats(request: HttpRequest, workflow_id: int | None = None):
    """
    GET /api/executions/stats

    Return aggregated execution statistics for the authenticated user.
    """
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    queryset = WorkflowExecution.objects.filter(thread__user=u)

    if workflow_id is not None:
        queryset = queryset.filter(workflow_id=workflow_id)

    stats = queryset.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status="completed")),
        running=Count("id", filter=Q(status="running")),
        pending=Count("id", filter=Q(status="pending")),
        failed=Count("id", filter=Q(status="failed")),
    )

    return ExecutionStatsSchema(
        total_executions=stats["total"],
        completed=stats["completed"],
        running=stats["running"],
        pending=stats["pending"],
        failed=stats["failed"],
        avg_duration_seconds=None,
    )


class ExecutionArtifactsSchema(Schema):
    """GET /executions/{id}/artifacts — 供前端预览与导出入口。"""

    execution_id: int
    status: str
    has_canvas_outputs: bool
    article_text: str
    media: dict


class ImageFromTextIn(Schema):
    """POST /executions/{id}/media/image-from-text"""

    prompt_suffix: str = ""
    size: str = "1024x1024"


class TtsRequestIn(Schema):
    """POST /executions/{id}/media/tts"""

    voice: str = "alloy"
    format: str = "mp3"


def _execution_qs(request: HttpRequest):
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    return WorkflowExecution.objects.select_related("workflow", "thread").filter(thread__user=u)


def _allowed_media_urls(exec_obj: WorkflowExecution) -> set[str]:
    media = collect_media_artifacts(exec_obj.output_data or {})
    urls: set[str] = set()
    for lst in media.values():
        for it in lst:
            u = it.get("url")
            if isinstance(u, str):
                urls.add(u.strip())
    return urls


@exec_router.get("/{execution_id}/artifacts", response={200: ExecutionArtifactsSchema, 404: MessageSchema})
def get_execution_artifacts(request: HttpRequest, execution_id: int):
    """
    解析 ``output_data``：正文、图片/音频/视频 URL 列表，供预览与下载按钮使用。
    """
    exec_obj = get_object_or_404(_execution_qs(request), id=execution_id)
    out = exec_obj.output_data or {}
    text = extract_primary_article_text(out) if isinstance(out, dict) else ""
    media = collect_media_artifacts(out) if isinstance(out, dict) else {"images": [], "audios": [], "videos": []}
    return 200, ExecutionArtifactsSchema(
        execution_id=exec_obj.id,
        status=exec_obj.status,
        has_canvas_outputs=isinstance(out, dict) and isinstance(out.get("outputs"), dict),
        article_text=text,
        media=media,
    )


@exec_router.get("/{execution_id}/export/article")
def export_execution_article(
    request: HttpRequest,
    execution_id: int,
    format: str = Query("txt", description="txt 或 docx"),
):
    """下载合并正文为 ``.txt`` 或 ``.docx``。"""
    exec_obj = get_object_or_404(_execution_qs(request), id=execution_id)
    if exec_obj.status != "completed":
        return HttpResponse("仅已完成执行可导出", status=409, content_type="text/plain; charset=utf-8")
    body = extract_primary_article_text(exec_obj.output_data or {})
    if not (body or "").strip():
        return HttpResponse("无可导出正文", status=400, content_type="text/plain; charset=utf-8")
    fmt = (format or "txt").strip().lower()
    if fmt == "txt":
        resp = HttpResponse(body.encode("utf-8"), content_type="text/plain; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="flowly-run-{execution_id}.txt"'
        return resp
    if fmt == "docx":
        title = exec_obj.workflow.name if exec_obj.workflow else "Flowly"
        raw = build_docx_bytes(title, body)
        return FileResponse(
            BytesIO(raw),
            as_attachment=True,
            filename=f"flowly-run-{execution_id}.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    return HttpResponse("format 仅支持 txt 或 docx", status=400, content_type="text/plain; charset=utf-8")


@exec_router.get("/{execution_id}/export/image")
def export_execution_image(
    request: HttpRequest,
    execution_id: int,
    format: str = Query("png", description="png / jpeg / webp"),
):
    """
    将执行结果中**首个**可访问的图片 URL 转为指定格式并下载。
    若节点仅产出文字描述而无 URL，请使用 ``POST .../media/image-from-text``。
    """
    exec_obj = get_object_or_404(_execution_qs(request), id=execution_id)
    if exec_obj.status != "completed":
        return HttpResponse("仅已完成执行可导出", status=409, content_type="text/plain; charset=utf-8")
    media = collect_media_artifacts(exec_obj.output_data or {})
    imgs = media.get("images") or []
    if not imgs:
        return HttpResponse("当前执行无图片 URL，可用「文生图」接口。", status=404, content_type="text/plain; charset=utf-8")
    url = str(imgs[0]["url"])
    try:
        raw, _ct = fetch_url_bytes(url)
    except Exception as exc:
        return HttpResponse(f"拉取图片失败: {exc}", status=502, content_type="text/plain; charset=utf-8")
    tgt = (format or "png").strip().lower()
    if tgt == "jpg":
        tgt = "jpeg"
    try:
        out_bytes, mime = convert_image_bytes(raw, tgt)
    except Exception as exc:
        return HttpResponse(str(exc), status=500, content_type="text/plain; charset=utf-8")
    ext = "jpg" if tgt == "jpeg" else tgt
    return FileResponse(
        BytesIO(out_bytes),
        as_attachment=True,
        filename=f"flowly-run-{execution_id}.{ext}",
        content_type=mime,
    )


@exec_router.get("/{execution_id}/export/proxy")
def export_proxy_media(
    request: HttpRequest,
    execution_id: int,
    url: str = Query(..., min_length=8, max_length=2048),
):
    """带鉴权的中转下载/预览（url 必须出现在该次执行的 output 中）。"""
    exec_obj = get_object_or_404(_execution_qs(request), id=execution_id)
    if url.strip() not in _allowed_media_urls(exec_obj):
        return HttpResponse("URL 不在本次执行结果内", status=403, content_type="text/plain; charset=utf-8")
    try:
        raw, ct = fetch_url_bytes(url.strip())
    except Exception as exc:
        return HttpResponse(f"拉取失败: {exc}", status=502, content_type="text/plain; charset=utf-8")
    return HttpResponse(raw, content_type=ct or "application/octet-stream")


@exec_router.post("/{execution_id}/media/image-from-text")
def generate_image_from_execution_text(
    request: HttpRequest,
    execution_id: int,
    body: ImageFromTextIn,
):
    """
    根据本次执行的合并正文 + 可选后缀调用 OpenAI 文生图（需 ``OPENAI_API_KEY``），返回 PNG 附件。
    前端可另请求 ``format=jpeg`` 的二次转换或自行处理。
    """
    exec_obj = get_object_or_404(_execution_qs(request), id=execution_id)
    if exec_obj.status != "completed":
        return HttpResponse("仅已完成执行可使用文生图", status=409, content_type="text/plain; charset=utf-8")
    base = extract_primary_article_text(exec_obj.output_data or {})
    suf = (body.prompt_suffix or "").strip()
    prompt = (base[:2800] + ("\n\n" + suf if suf else "")).strip()
    if not prompt:
        return HttpResponse("无可用于文生图的文本", status=400, content_type="text/plain; charset=utf-8")
    try:
        raw, mime = openai_text_to_image_bytes(prompt=prompt, size=body.size or "1024x1024")
    except ValueError as ve:
        return HttpResponse(str(ve), status=400, content_type="text/plain; charset=utf-8")
    except Exception as exc:
        return HttpResponse(f"文生图失败: {exc}", status=502, content_type="text/plain; charset=utf-8")
    return FileResponse(
        BytesIO(raw),
        as_attachment=True,
        filename=f"flowly-run-{execution_id}-generated.png",
        content_type=mime,
    )


@exec_router.post("/{execution_id}/media/tts")
def synthesize_speech_from_execution_text(
    request: HttpRequest,
    execution_id: int,
    body: TtsRequestIn,
):
    """将合并正文前 4096 字转为语音（OpenAI TTS，需 ``OPENAI_API_KEY``）。"""
    exec_obj = get_object_or_404(_execution_qs(request), id=execution_id)
    if exec_obj.status != "completed":
        return HttpResponse("仅已完成执行可合成语音", status=409, content_type="text/plain; charset=utf-8")
    text = extract_primary_article_text(exec_obj.output_data or {})
    if not text.strip():
        return HttpResponse("无可朗读文本", status=400, content_type="text/plain; charset=utf-8")
    try:
        audio, mime = openai_tts_bytes(
            text=text,
            voice=body.voice,
            response_format=(body.format or "mp3").lower(),
        )
    except ValueError as ve:
        return HttpResponse(str(ve), status=400, content_type="text/plain; charset=utf-8")
    except Exception as exc:
        return HttpResponse(f"TTS 失败: {exc}", status=502, content_type="text/plain; charset=utf-8")
    ext = body.format if body.format in ("mp3", "opus", "aac", "flac", "wav") else "mp3"
    return FileResponse(
        BytesIO(audio),
        as_attachment=True,
        filename=f"flowly-run-{execution_id}.{ext}",
        content_type=mime,
    )


@exec_router.get("/{execution_id}/export/image-generated")
def export_image_generated_as_format(
    request: HttpRequest,
    execution_id: int,
    format: str = Query("png", description="png / jpeg / webp，基于文生图 PNG 再编码"),
    prompt_suffix: str = Query(""),
    size: str = Query("1024x1024"),
):
    """
    单次请求内：文生图 → 再转 jpeg/webp（便于仅 GET 的场景）。
    依赖 ``OPENAI_API_KEY``。
    """
    exec_obj = get_object_or_404(_execution_qs(request), id=execution_id)
    if exec_obj.status != "completed":
        return HttpResponse("仅已完成执行可导出", status=409, content_type="text/plain; charset=utf-8")
    base = extract_primary_article_text(exec_obj.output_data or {})
    suf = (prompt_suffix or "").strip()
    prompt = (base[:2800] + ("\n\n" + suf if suf else "")).strip()
    if not prompt:
        return HttpResponse("无可用于文生图的文本", status=400, content_type="text/plain; charset=utf-8")
    try:
        raw_png, _ = openai_text_to_image_bytes(prompt=prompt, size=size or "1024x1024")
    except Exception as exc:
        return HttpResponse(f"文生图失败: {exc}", status=502, content_type="text/plain; charset=utf-8")
    tgt = (format or "png").strip().lower()
    if tgt == "jpg":
        tgt = "jpeg"
    if tgt == "png":
        return FileResponse(
            BytesIO(raw_png),
            as_attachment=True,
            filename=f"flowly-run-{execution_id}.png",
            content_type="image/png",
        )
    try:
        out_bytes, mime = convert_image_bytes(raw_png, tgt)
    except Exception as exc:
        return HttpResponse(str(exc), status=500, content_type="text/plain; charset=utf-8")
    ext = "jpg" if tgt == "jpeg" else tgt
    return FileResponse(
        BytesIO(out_bytes),
        as_attachment=True,
        filename=f"flowly-run-{execution_id}.{ext}",
        content_type=mime,
    )


@exec_router.get("/{execution_id}", response={200: ExecutionResponseSchema, 404: MessageSchema})
def get_execution(request: HttpRequest, execution_id: int):
    """
    GET /api/executions/{id}

    Retrieve a single execution by ID.
    """
    exec_obj = get_object_or_404(_execution_qs(request), id=execution_id)
    return 200, _execution_to_response(exec_obj)
