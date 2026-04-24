from __future__ import annotations

from typing import Any, Mapping

from django.db import transaction

from ai_engine.models import Workflow, WorkflowGraphEdge, WorkflowGraphNode


class WorkflowGraphRepository:
    """
    工作流画布节点与边的持久化仓库（Repository 模式）。

    事务语义
    --------
    ``replace_graph`` 在**单个数据库事务**内先删后插同一 ``workflow`` 下的全部
    图记录，避免出现「边已写入、节点未写完」的中间状态被其他请求读到。

    调用方责任
    ----------
    - 写入前剥离 ``config`` / ``metadata`` 中的密钥、Cookie、个人隐私字段。
    - 保证 ``client_node_id`` / ``client_edge_id`` 在单次保存批次内唯一且与前端
      Vue Flow 等编辑器中的 id 一致，便于增量更新或 diff（若未来需要）。
    """

    @staticmethod
    def replace_graph(
        workflow: Workflow,
        *,
        nodes: list[Mapping[str, Any]],
        edges: list[Mapping[str, Any]],
    ) -> None:
        """
        用本次提交的数据**全量替换**该工作流在 MySQL 中的图镜像。

        Args:
            workflow: 已存在的 ``Workflow`` 实例（外键目标）。
            nodes: 节点字典列表，每个字典建议包含：
                - ``client_node_id`` (必填): 编辑器中的稳定节点 id。
                - ``node_type`` (可选): 缺省为 ``"custom"``，与 ``NodeTypeId`` 对齐。
                - ``title``, ``position_x``, ``position_y``, ``z_index`` (可选)
                - ``config`` (可选): dict，**不得**含 API Key。
            edges: 边字典列表，每个字典建议包含：
                - ``client_edge_id`` (必填)
                - ``source_node_id`` / ``target_node_id`` (必填): 对应节点的 ``client_node_id``
                - ``source_handle`` / ``target_handle`` (可选): 多端口连线时的句柄名
                - ``metadata`` (可选): dict，同样勿存敏感信息

        Raises:
            KeyError: 若某条 node/edge 缺少必填键；调用方应在进入本方法前做校验，
                或在此方法外加 try/convert 为业务异常。

        Note:
            本方法**不**更新 ``Workflow.definition``；若需双写，由 API 层先后调用
            ``workflow.save()`` 与本仓库方法，并注意两者失败时的回滚策略。
        """
        with transaction.atomic():
            # 先清空旧图，再 bulk_create：比逐条 upsert 更简单，适合「整画布保存」
            WorkflowGraphNode.objects.filter(workflow=workflow).delete()
            WorkflowGraphEdge.objects.filter(workflow=workflow).delete()
            WorkflowGraphNode.objects.bulk_create(
                [
                    WorkflowGraphNode(
                        workflow=workflow,
                        client_node_id=str(n["client_node_id"]),
                        node_type=str(n.get("node_type", "custom")),
                        title=str(n.get("title", ""))[:255],
                        position_x=float(n.get("position_x", 0.0)),
                        position_y=float(n.get("position_y", 0.0)),
                        z_index=int(n.get("z_index", 0)),
                        config=dict(n.get("config", {})),
                    )
                    for n in nodes
                ]
            )
            WorkflowGraphEdge.objects.bulk_create(
                [
                    WorkflowGraphEdge(
                        workflow=workflow,
                        client_edge_id=str(e["client_edge_id"]),
                        source_node_id=str(e["source_node_id"]),
                        target_node_id=str(e["target_node_id"]),
                        source_handle=str(e.get("source_handle", ""))[:64],
                        target_handle=str(e.get("target_handle", ""))[:64],
                        metadata=dict(e.get("metadata", {})),
                    )
                    for e in edges
                ]
            )
