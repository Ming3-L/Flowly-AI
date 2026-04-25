"""
工作流 CRUD API —— 列表、新建、详情、更新与删除。

所有接口均需通过 HttpBearer 携带 JWT 鉴权。
列表与详情：普通用户仅本人；管理员可读全站。更新与删除仍为创建者本人。
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import Workflow, WorkflowExecution, Thread, WorkflowGraphValidation
from .workflow_graph.definition_sync import sync_workflow_graph_from_definition
from .workflow_graph.validator import validate_workflow_definition

User = get_user_model()
workflow_crud_router = Router(tags=["Workflows CRUD"], auth=JWTAuth())


class WorkflowCreateSchema(Schema):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    definition: dict = Field(default_factory=dict)


class WorkflowUpdateSchema(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    definition: dict | None = None
    is_active: bool | None = None


class WorkflowResponseSchema(Schema):
    id: int
    name: str
    description: str
    definition: dict
    is_active: bool
    created_at: str
    updated_at: str
    execution_count: int = 0
    thread_count: int = 0
    owner_user_id: int | None = None
    owner_username: str = ""


class WorkflowListSchema(Schema):
    total: int
    items: list[WorkflowResponseSchema]


class MessageSchema(Schema):
    message: str
    detail: str | None = None


class WorkflowValidationErrorSchema(Schema):
    message: str
    errors: list[dict[str, str]]


def _workflow_to_response(wf: Workflow) -> WorkflowResponseSchema:
    uid = getattr(wf, "user_id", None)
    uname = ""
    if uid and getattr(wf, "user", None):
        uname = str(getattr(wf.user, "username", "") or "")
    return WorkflowResponseSchema(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        definition=wf.definition or {},
        is_active=wf.is_active,
        created_at=wf.created_at.isoformat() if wf.created_at else "",
        updated_at=wf.updated_at.isoformat() if wf.updated_at else "",
        execution_count=WorkflowExecution.objects.filter(workflow=wf).count(),
        thread_count=Thread.objects.filter(workflow=wf).count(),
        owner_user_id=int(uid) if uid else None,
        owner_username=uname,
    )


@workflow_crud_router.get("/", response=WorkflowListSchema)
def list_workflows(request: HttpRequest, search: str = "", is_active: bool | None = None):
    """GET /api/workflows/ —— 列出工作流；普通用户仅本人，管理员（is_staff）可见全站。"""
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    staff = bool(getattr(u, "is_staff", False) or getattr(u, "is_superuser", False))
    queryset = Workflow.objects.filter(is_deleted=False)
    if not staff:
        queryset = queryset.filter(user=u)

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    items = [_workflow_to_response(wf) for wf in queryset.select_related("user").order_by("-created_at")]

    return WorkflowListSchema(total=len(items), items=items)


@workflow_crud_router.post("/", response={201: WorkflowResponseSchema, 400: WorkflowValidationErrorSchema})
def create_workflow(request: HttpRequest, payload: WorkflowCreateSchema):
    """POST /api/workflows/ —— 为当前已认证用户创建工作流。"""
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    ok, errors = validate_workflow_definition(payload.definition or {}, user_id=getattr(u, "id", None))
    if not ok:
        return 400, WorkflowValidationErrorSchema(message="工作流校验失败", errors=errors)
    with transaction.atomic():
        wf = Workflow.objects.create(
            user=u,
            name=payload.name,
            description=payload.description,
            definition=payload.definition or {},
            is_active=True,
            is_deleted=False,
            deleted_at=None,
        )
        sync_workflow_graph_from_definition(wf, wf.definition if isinstance(wf.definition, dict) else {})
        WorkflowGraphValidation.objects.update_or_create(
            workflow=wf,
            defaults={"is_valid": True, "errors": []},
        )
    return 201, _workflow_to_response(wf)


@workflow_crud_router.get("/{workflow_id}", response=WorkflowResponseSchema)
def get_workflow(request: HttpRequest, workflow_id: int):
    """GET /api/workflows/{id} — 管理员可读任意工作流；普通用户仅本人。"""
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    staff = bool(getattr(u, "is_staff", False) or getattr(u, "is_superuser", False))
    if staff:
        wf = get_object_or_404(Workflow.objects.select_related("user"), id=workflow_id, is_deleted=False)
    else:
        wf = get_object_or_404(
            Workflow.objects.select_related("user"), id=workflow_id, user=u, is_deleted=False
        )
    return 200, _workflow_to_response(wf)


@workflow_crud_router.put("/{workflow_id}", response={200: WorkflowResponseSchema, 400: WorkflowValidationErrorSchema})
def update_workflow(request: HttpRequest, workflow_id: int, payload: WorkflowUpdateSchema):
    """PUT /api/workflows/{id}"""
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    wf = get_object_or_404(Workflow, id=workflow_id, user=u, is_deleted=False)

    with transaction.atomic():
        if payload.name is not None:
            wf.name = payload.name
        if payload.description is not None:
            wf.description = payload.description
        if payload.definition is not None:
            ok, errors = validate_workflow_definition(payload.definition or {}, user_id=getattr(request.user, "id", None))
            if not ok:
                return 400, WorkflowValidationErrorSchema(message="工作流校验失败", errors=errors)
            wf.definition = payload.definition
        if payload.is_active is not None:
            wf.is_active = payload.is_active

        wf.save()
        # definition 为权威；MySQL 图为从属镜像，失败则整段事务回滚（见 definition_sync 文档）
        sync_workflow_graph_from_definition(wf, wf.definition if isinstance(wf.definition, dict) else {})
        WorkflowGraphValidation.objects.update_or_create(
            workflow=wf,
            defaults={"is_valid": True, "errors": []},
        )

    return 200, _workflow_to_response(wf)


@workflow_crud_router.delete("/{workflow_id}", response=MessageSchema)
def delete_workflow(request: HttpRequest, workflow_id: int):
    """DELETE /api/workflows/{id} —— 软删除（is_deleted=True）。"""
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    wf = get_object_or_404(Workflow, id=workflow_id, user=u, is_deleted=False)
    wf.is_deleted = True
    wf.deleted_at = timezone.now()
    wf.save(update_fields=["is_deleted", "deleted_at"])
    return 200, MessageSchema(
        message="工作流已删除",
        detail=f"工作流「{wf.name}」已删除",
    )
