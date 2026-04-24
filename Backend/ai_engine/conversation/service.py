from __future__ import annotations

from typing import Any, Mapping

from django.db import transaction

from ai_engine.models import ConversationMessage, ConversationSession, Workflow


class AutoReplyOrchestrator:
    """
    自动回复 / 多轮对话编排的占位服务类。

    设计意图
    --------
    - **append_user_message**：同步路径下安全落库用户消息（带行级锁，避免并发下
      会话元数据与消息序号错乱；若后续按序号展示，可扩展 ``metadata``）。
    - **draft_reply**：预留异步或同步生成助手回复；内部应组合
      ``ConversationMessage`` 历史 + 可选 ``session.workflow`` 定义的 LangGraph，
      并通过 ``get_ai_provider_settings()`` 取密钥。
    - **attach_workflow**：把某会话绑定到指定工作流，便于「每个客服会话走不同 bot」。

    安全
    ----
    公共方法签名中**不要**出现 ``api_key`` 等参数；密钥只能在服务端进程内读取。
    """

    @staticmethod
    @transaction.atomic
    def append_user_message(
        *,
        session_id: int,
        content: str,
        attachments: list[Mapping[str, Any]] | None = None,
    ) -> ConversationMessage:
        """
        在指定会话中追加一条用户消息并返回 ORM 实例。

        Args:
            session_id: ``ConversationSession`` 主键。
            content: 纯文本内容；富文本可序列化后存此处或拆到 ``metadata``。
            attachments: 可选附件列表，例如
                ``[{"type": "image", "url": "..."}]`` —— URL 应为短时签名链接，
                避免永久暴露私有对象存储路径。

        Returns:
            已持久化的 ``ConversationMessage``（role=user）。

        Note:
            使用 ``select_for_update()`` 锁定会话行，防止与并发的「关闭会话」等
            操作产生竞态；若 QPS 极高可再评估锁粒度。
        """
        # select_for_update：锁定会话行；session 实例同时作为外键写入消息
        session = ConversationSession.objects.select_for_update().get(pk=session_id)
        return ConversationMessage.objects.create(
            session=session,
            role=ConversationMessage.Role.USER,
            content=content,
            attachments=list(attachments or []),
        )

    def draft_reply(self, *, session_id: int) -> str:
        """
        （未实现）根据会话历史与会话绑定的 ``Workflow`` 生成助手回复正文。

        Args:
            session_id: 目标会话。

        Returns:
            助手可见的纯文本（或后续扩展为结构化 payload）。

        Raises:
            NotImplementedError: 当前占位；实现时应改为业务异常或空回复策略。
        """
        raise NotImplementedError("Connect LangGraph + provider here; keys only from env.")

    @staticmethod
    def attach_workflow(session_id: int, workflow: Workflow) -> None:
        """
        将会话与某条 ``Workflow`` 定义关联，供后续 ``draft_reply`` 选择图定义。

        Args:
            session_id: 会话主键。
            workflow: 已存在的 ``Workflow`` 实例；若工作流被删除，外键策略为
                ``SET_NULL`` 时会话上该字段会被置空（见模型定义）。
        """
        ConversationSession.objects.filter(pk=session_id).update(workflow=workflow)
