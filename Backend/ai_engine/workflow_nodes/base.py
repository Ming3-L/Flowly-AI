from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class NodeExecutor(ABC):
    """
    单个工作流节点的执行接口（策略模式）。

    约定
    ----
    - ``config``: 通常来自数据库 ``WorkflowGraphNode.config``，只应包含**非敏感**
      参数（提示词模板、温度、是否流式等）。密钥必须从 ``integrations`` 读取。
    - ``inputs``: 上游节点已解析好的输入字典；键名由编排引擎定义（例如边标签、
      端口 id）。执行器应做好缺省键的容错或明确报错。
    - 返回值: 下游节点可读的结构化 dict；若节点产生副作用（写文件、发消息），
      建议把可追踪 id 一并放进返回值，便于 ``WorkflowExecution`` 审计。

    实现类位置
    ----------
    各具体类型放在 ``workflow_nodes/types/`` 下，便于按介质（文本/音视频）分文件维护。
    """

    @abstractmethod
    def execute(self, *, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        执行本节点逻辑并返回输出。

        Args:
            config: 节点静态配置（来自 DB，无密钥）。
            inputs: 上游聚合输入。

        Returns:
            供下游消费的纯数据 dict；具体键名由项目内规范文档约定。
        """
        ...
