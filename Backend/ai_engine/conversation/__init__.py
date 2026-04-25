"""
conversation 包：AI 对话会话、自动回复编排的**业务入口**（当前多为预留）。

定位
----
- 数据模型：``ConversationSession`` / ``ConversationMessage``（见 ``ai_engine.models``）。
- 服务类：``AutoReplyOrchestrator``（``service.py``）封装「写用户消息、生成助手回复、
  绑定工作流」等用例级 API，避免视图层直接堆 ORM。

参考实现（仅注释说明，不引入外部依赖）
----------------------------------------
仓库内与本功能对齐的参考实现见 ``ai_engine/desktop_screen_agent/ocr_reference_bundle``。
若你本地另有「渠道消息 → LLM → 回写」项目，可自行对照（勿把本地路径或密钥提交仓库）。

将其中与渠道耦合的适配器放在未来子模块（如 ``conversation.channels``），
与本包核心编排解耦。
"""

from ai_engine.conversation.service import AutoReplyOrchestrator

__all__ = ["AutoReplyOrchestrator"]
