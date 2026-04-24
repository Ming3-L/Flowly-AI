from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ai_engine.models import UserCustomNodeType


BUILTIN_NODE_TYPES: tuple[str, ...] = (
    "chat",
    "tool",
    "condition",
    "human_approval",
    "parallel",
    "text",
    "image",
    "audio",
    "video",
)


def _is_ut_type(node_type: str) -> bool:
    return bool(node_type) and node_type.startswith("ut_") and node_type[3:].isdigit()


def _allowed_source_handles(node_type: str) -> set[str]:
    nt = (node_type or "").strip()
    if nt == "condition":
        return {"true", "false"}
    if nt == "human_approval":
        return {"approved", "rejected"}
    return {"out"}


def _allowed_target_handles(_node_type: str) -> set[str]:
    return {"in"}


@dataclass(frozen=True)
class ValidationErrorItem:
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


def validate_workflow_definition(
    definition: dict[str, Any],
    *,
    user_id: int | None,
) -> tuple[bool, list[dict[str, str]]]:
    """
    严格校验 Workflow.definition（前端 workflow-editor.ts 形状）。

    返回：
        (ok, errors)
    """
    errors: list[ValidationErrorItem] = []

    if not isinstance(definition, dict):
        errors.append(ValidationErrorItem(path="definition", code="type", message="definition 必须为 JSON object"))
        return False, [e.as_dict() for e in errors]

    raw_nodes = definition.get("nodes")
    raw_edges = definition.get("edges")

    if not isinstance(raw_nodes, list) or len(raw_nodes) == 0:
        errors.append(ValidationErrorItem(path="nodes", code="required", message="nodes 必须为非空数组"))
        return False, [e.as_dict() for e in errors]

    if raw_edges is None:
        raw_edges = []
    if not isinstance(raw_edges, list):
        errors.append(ValidationErrorItem(path="edges", code="type", message="edges 必须为数组"))
        return False, [e.as_dict() for e in errors]

    node_ids: list[str] = []
    node_type_by_id: dict[str, str] = {}

    # ── Nodes ──────────────────────────────────────────────────────────────
    for i, n in enumerate(raw_nodes):
        pfx = f"nodes[{i}]"
        if not isinstance(n, dict):
            errors.append(ValidationErrorItem(path=pfx, code="type", message="节点必须为 object"))
            continue

        nid = str(n.get("id") or "").strip()
        if not nid:
            errors.append(ValidationErrorItem(path=f"{pfx}.id", code="required", message="节点 id 不能为空"))
        elif len(nid) > 128:
            errors.append(ValidationErrorItem(path=f"{pfx}.id", code="max_length", message="节点 id 长度不能超过 128"))
        else:
            node_ids.append(nid)

        ntype = str(n.get("type") or "").strip()
        if not ntype:
            errors.append(ValidationErrorItem(path=f"{pfx}.type", code="required", message="节点 type 不能为空"))
        else:
            if ntype not in BUILTIN_NODE_TYPES and not _is_ut_type(ntype):
                errors.append(ValidationErrorItem(path=f"{pfx}.type", code="invalid", message=f"未知节点类型: {ntype}"))
            if _is_ut_type(ntype):
                # 归属校验：ut_<pk> 必须属于该用户（若传入 user_id）
                pk = int(ntype[3:])
                qs = UserCustomNodeType.objects.filter(pk=pk)
                if user_id is not None:
                    qs = qs.filter(user_id=user_id)
                if not qs.exists():
                    errors.append(
                        ValidationErrorItem(
                            path=f"{pfx}.type",
                            code="forbidden",
                            message=f"自定义节点类型不可用或无权限: {ntype}",
                        )
                    )

        label = str(n.get("label") or "").strip()
        if not label:
            errors.append(ValidationErrorItem(path=f"{pfx}.label", code="required", message="节点名称(label)不能为空"))

        if nid:
            node_type_by_id[nid] = ntype

    # 唯一性校验
    seen: set[str] = set()
    for nid in node_ids:
        if nid in seen:
            errors.append(ValidationErrorItem(path="nodes", code="duplicate_id", message=f"节点 id 重复: {nid}"))
        seen.add(nid)

    node_id_set = set(node_ids)

    # ── Edges ──────────────────────────────────────────────────────────────
    edge_ids: list[str] = []
    for i, e in enumerate(raw_edges):
        pfx = f"edges[{i}]"
        if not isinstance(e, dict):
            errors.append(ValidationErrorItem(path=pfx, code="type", message="边必须为 object"))
            continue

        eid = str(e.get("id") or "").strip()
        if not eid:
            errors.append(ValidationErrorItem(path=f"{pfx}.id", code="required", message="边 id 不能为空"))
        elif len(eid) > 128:
            errors.append(ValidationErrorItem(path=f"{pfx}.id", code="max_length", message="边 id 长度不能超过 128"))
        else:
            edge_ids.append(eid)

        src = str(e.get("sourceNodeId") or "").strip()
        tgt = str(e.get("targetNodeId") or "").strip()
        if not src:
            errors.append(ValidationErrorItem(path=f"{pfx}.sourceNodeId", code="required", message="sourceNodeId 不能为空"))
        elif src not in node_id_set:
            errors.append(ValidationErrorItem(path=f"{pfx}.sourceNodeId", code="dangling_ref", message=f"sourceNodeId 不存在: {src}"))

        if not tgt:
            errors.append(ValidationErrorItem(path=f"{pfx}.targetNodeId", code="required", message="targetNodeId 不能为空"))
        elif tgt not in node_id_set:
            errors.append(ValidationErrorItem(path=f"{pfx}.targetNodeId", code="dangling_ref", message=f"targetNodeId 不存在: {tgt}"))

        if src and tgt and src == tgt:
            errors.append(ValidationErrorItem(path=pfx, code="self_loop", message="不允许自环（sourceNodeId == targetNodeId）"))

        sh = str(e.get("sourcePortId") or "").strip() or "out"
        th = str(e.get("targetPortId") or "").strip() or "in"

        src_type = node_type_by_id.get(src, "")
        tgt_type = node_type_by_id.get(tgt, "")

        if src and src in node_id_set:
            allowed = _allowed_source_handles(src_type)
            if sh not in allowed:
                errors.append(
                    ValidationErrorItem(
                        path=f"{pfx}.sourcePortId",
                        code="invalid_handle",
                        message=f"sourcePortId={sh} 不合法（节点 {src} 类型 {src_type} 允许 {sorted(allowed)}）",
                    )
                )

        if tgt and tgt in node_id_set:
            allowed_t = _allowed_target_handles(tgt_type)
            if th not in allowed_t:
                errors.append(
                    ValidationErrorItem(
                        path=f"{pfx}.targetPortId",
                        code="invalid_handle",
                        message=f"targetPortId={th} 不合法（目标节点 {tgt} 允许 {sorted(allowed_t)}）",
                    )
                )

    # 边 id 唯一性校验
    seen_e: set[str] = set()
    for eid in edge_ids:
        if eid in seen_e:
            errors.append(ValidationErrorItem(path="edges", code="duplicate_id", message=f"边 id 重复: {eid}"))
        seen_e.add(eid)

    ok = len(errors) == 0
    return ok, [e.as_dict() for e in errors]

