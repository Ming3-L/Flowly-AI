"""
Workflow CRUD API — list, create, retrieve, update, delete.

All endpoints require JWT authentication via HttpBearer.
Each user only sees and manages their own workflows.
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
    )


@workflow_crud_router.get("/", response=WorkflowListSchema)
def list_workflows(request: HttpRequest, search: str = "", is_active: bool | None = None):
    """GET /api/workflows/ — list workflows for the authenticated user"""
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    queryset = Workflow.objects.filter(user=u, is_deleted=False)

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    items = [_workflow_to_response(wf) for wf in queryset.order_by("-created_at")]

    return WorkflowListSchema(total=len(items), items=items)


@workflow_crud_router.post("/", response={201: WorkflowResponseSchema, 400: WorkflowValidationErrorSchema})
def create_workflow(request: HttpRequest, payload: WorkflowCreateSchema):
    """POST /api/workflows/ — create a new workflow for the authenticated user"""
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
    """GET /api/workflows/{id}"""
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    wf = get_object_or_404(Workflow, id=workflow_id, user=u, is_deleted=False)
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
    """DELETE /api/workflows/{id} — soft-delete (is_deleted=True)"""
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    wf = get_object_or_404(Workflow, id=workflow_id, user=u, is_deleted=False)
    wf.is_deleted = True
    wf.deleted_at = timezone.now()
    wf.save(update_fields=["is_deleted", "deleted_at"])
    return 200, MessageSchema(
        message="Workflow deleted",
        detail=f"Workflow '{wf.name}' has been deleted",
    )
