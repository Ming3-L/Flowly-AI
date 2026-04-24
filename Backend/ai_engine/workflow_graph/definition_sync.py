"""
``Workflow.definition``（JSON）与 ``WorkflowGraphNode`` / ``WorkflowGraphEdge`` 的同步策略。

谁为准（canonical source）
--------------------------
- **运行时执行与版本回溯**：以 ``Workflow.definition`` 为权威快照；LangGraph / 前端
  编辑器均基于该 JSON。
- **SQL 统计、计费维度、运维查询**：以规范化表为**从属镜像**；由保存 API 在
  同一事务内从 definition 派生写入。

双写失败与回滚
--------------
- 仅当 ``definition`` 成功写入 ``Workflow`` 行后，在同一 ``transaction.atomic()`` 内
  调用 ``WorkflowGraphRepository.replace_graph``。
- 若 ``replace_graph`` 抛错，整段事务回滚，**definition 也不会落库**，避免「JSON
  已更新但 MySQL 图缺边」的不一致。
- 若业务将来需要「definition 先成功、图异步补写」，必须引入显式 ``graph_sync_status``
  字段与补偿任务；当前实现不采用该模式。
"""

from __future__ import annotations

from typing import Any

from ai_engine.models import Workflow
from ai_engine.workflow_graph.config_sanitizer import strip_sensitive_config
from ai_engine.workflow_graph.repository import WorkflowGraphRepository


def definition_to_graph_rows(
    definition: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    将编辑器 ``definition``（含 ``nodes`` / ``edges``）转为 ``replace_graph`` 所需列表。

    兼容 ``workflowEditor`` store 形状：``nodes[].id``、``type``、``label``、``x``/``y``、
    ``config``；``edges[].id``、``sourceNodeId``、``targetNodeId``、端口 id。
    """
    raw_nodes = definition.get("nodes") or []
    raw_edges = definition.get("edges") or []

    nodes: list[dict[str, Any]] = []
    for n in raw_nodes:
        if not isinstance(n, dict) or not n.get("id"):
            continue
        cfg = strip_sensitive_config(n.get("config") or {})
        nodes.append(
            {
                "client_node_id": str(n["id"]),
                "node_type": str(n.get("type", "custom"))[:64],
                "title": str(n.get("label", ""))[:255],
                "position_x": float(n.get("x", 0.0)),
                "position_y": float(n.get("y", 0.0)),
                "z_index": int(n.get("zIndex", n.get("z_index", 0))),
                "config": cfg,
            }
        )

    edges: list[dict[str, Any]] = []
    for e in raw_edges:
        if not isinstance(e, dict) or not e.get("id"):
            continue
        edges.append(
            {
                "client_edge_id": str(e["id"]),
                "source_node_id": str(e.get("sourceNodeId", "")),
                "target_node_id": str(e.get("targetNodeId", "")),
                "source_handle": str(e.get("sourcePortId", ""))[:64],
                "target_handle": str(e.get("targetPortId", ""))[:64],
                "metadata": {},
            }
        )
    return nodes, edges


def sync_workflow_graph_from_definition(workflow: Workflow, definition: dict[str, Any]) -> None:
    """根据 definition 全量刷新 MySQL 中的图镜像（调用方须已在事务内）。"""
    nodes, edges = definition_to_graph_rows(definition)
    WorkflowGraphRepository.replace_graph(workflow, nodes=nodes, edges=edges)
