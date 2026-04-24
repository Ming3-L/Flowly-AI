"""
节点类型 → ``NodeExecutor`` 实例解析。

内置类型与编辑器 ``EditorNodeType`` 对齐；用户自定义模板使用 ``ut_<主键>``。
"""

from __future__ import annotations

from enum import Enum
from typing import Final

from ai_engine.models import UserCustomNodeType
from ai_engine.workflow_nodes.base import NodeExecutor
from ai_engine.workflow_nodes.types.ai_chat_node import AIChatNodeExecutor
from ai_engine.workflow_nodes.types.audio_node import AudioNodeExecutor
from ai_engine.workflow_nodes.types.image_node import ImageNodeExecutor
from ai_engine.workflow_nodes.types.text_node import TextNodeExecutor
from ai_engine.workflow_nodes.types.user_custom_template_node import UserCustomTemplateNodeExecutor
from ai_engine.workflow_nodes.types.video_node import VideoNodeExecutor
from ai_engine.workflow_nodes.types.placeholder_node import PlaceholderNodeExecutor


class NodeTypeId(str, Enum):
    """文档用内置枚举；画布上还可出现 chat / tool 等编辑器类型。"""

    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    AI_CHAT = "ai_chat"
    CUSTOM = "custom"


NODE_TYPES: Final[tuple[str, ...]] = tuple(m.value for m in NodeTypeId)


# 编辑器内置类型 → 执行器（占位类型使用 PlaceholderNodeExecutor，错误信息见该类）
_BUILTIN_EXECUTORS: dict[str, NodeExecutor] = {
    "chat": AIChatNodeExecutor(),
    "ai_chat": AIChatNodeExecutor(),
    "text": TextNodeExecutor(),
    "audio": AudioNodeExecutor(),
    "image": ImageNodeExecutor(),
    "video": VideoNodeExecutor(),
    "tool": PlaceholderNodeExecutor("tool"),
    "condition": PlaceholderNodeExecutor("condition"),
    "human_approval": PlaceholderNodeExecutor("human_approval"),
    "parallel": PlaceholderNodeExecutor("parallel"),
    "custom": PlaceholderNodeExecutor("custom"),
}


def register_node_type(node_type: str) -> None:
    """（预留）动态注册插件节点类型。"""
    raise NotImplementedError("Dynamic node registration is reserved for a later phase.")


def resolve_node_executor(node_type: str, *, user_id: int | None) -> NodeExecutor:
    """
    根据 ``node_type`` 返回可执行实例。

    ``ut_<id>``：加载 ``UserCustomNodeType``，且 ``user_id`` 必须与所有者一致。
    """
    nt = (node_type or "").strip()
    if nt.startswith("ut_"):
        pk_str = nt[3:]
        if not pk_str.isdigit():
            raise ValueError(f"非法自定义节点键: {node_type}")
        pk = int(pk_str)
        qs = UserCustomNodeType.objects.filter(pk=pk)
        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        tmpl = qs.first()
        if tmpl is None:
            raise PermissionError("自定义节点类型不存在或无权使用")
        return UserCustomTemplateNodeExecutor(template=tmpl)
    ex = _BUILTIN_EXECUTORS.get(nt)
    if ex is None:
        raise LookupError(f"未注册的节点类型: {nt}")
    return ex
