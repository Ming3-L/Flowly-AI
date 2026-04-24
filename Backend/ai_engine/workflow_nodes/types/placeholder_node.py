"""尚未接入执行引擎的画布节点类型：明确报错，避免误用 TextNodeExecutor 的歧义信息。"""

from __future__ import annotations

from typing import Any, Mapping

from ai_engine.workflow_nodes.base import NodeExecutor


class PlaceholderNodeExecutor(NodeExecutor):
    def __init__(self, type_key: str) -> None:
        self._type_key = (type_key or "").strip() or "unknown"

    def execute(self, *, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError(
            f"画布节点类型「{self._type_key}」尚未接入执行引擎。"
            "请使用「对话 / chat」或已发布的自定义类型（ut_<id>）。"
        )
