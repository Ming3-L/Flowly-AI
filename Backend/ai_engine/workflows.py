"""
Workflow CRUD API — list, create, retrieve, update, delete.

All endpoints require JWT authentication via HttpBearer.
Each user only sees and manages their own workflows.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import Workflow, WorkflowExecution, Thread

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
    queryset = Workflow.objects.filter(user=request.user)

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    items = [_workflow_to_response(wf) for wf in queryset.order_by("-created_at")]

    return WorkflowListSchema(total=len(items), items=items)


@workflow_crud_router.post("/", response={201: WorkflowResponseSchema})
def create_workflow(request: HttpRequest, payload: WorkflowCreateSchema):
    """POST /api/workflows/ — create a new workflow for the authenticated user"""
    wf = Workflow.objects.create(
        user=request.user,
        name=payload.name,
        description=payload.description,
        definition=payload.definition or {},
        is_active=True,
    )
    return 201, _workflow_to_response(wf)


@workflow_crud_router.get("/{workflow_id}", response=WorkflowResponseSchema)
def get_workflow(request: HttpRequest, workflow_id: int):
    """GET /api/workflows/{id}"""
    wf = get_object_or_404(Workflow, id=workflow_id, user=request.user)
    return 200, _workflow_to_response(wf)


@workflow_crud_router.put("/{workflow_id}", response=WorkflowResponseSchema)
def update_workflow(request: HttpRequest, workflow_id: int, payload: WorkflowUpdateSchema):
    """PUT /api/workflows/{id}"""
    wf = get_object_or_404(Workflow, id=workflow_id, user=request.user)

    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description
    if payload.definition is not None:
        wf.definition = payload.definition
    if payload.is_active is not None:
        wf.is_active = payload.is_active

    wf.save()
    return 200, _workflow_to_response(wf)


@workflow_crud_router.delete("/{workflow_id}", response=MessageSchema)
def delete_workflow(request: HttpRequest, workflow_id: int):
    """DELETE /api/workflows/{id} — soft-delete by setting is_active=False"""
    wf = get_object_or_404(Workflow, id=workflow_id, user=request.user)
    wf.is_active = False
    wf.save(update_fields=["is_active"])
    return 200, MessageSchema(
        message="Workflow deactivated",
        detail=f"Workflow '{wf.name}' has been deactivated",
    )
