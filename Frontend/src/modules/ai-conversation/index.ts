/**
 * AI 对话与自动回复 —— 前端模块化入口（预留）
 *
 * 职责划分建议
 * ------------
 * - **类型**：与后端 ``ConversationMessage.role`` 对齐的角色字面量。
 * - **Store**：后续可用 Pinia 维护当前 ``sessionId``、消息列表分页、流式追加等。
 * - **API**：封装创建会话、拉取历史、发送用户消息、订阅助手流式输出（若走 SSE/WebSocket）。
 *
 * 安全
 * ----
 * 任何模型密钥、渠道 Token 仅在后端环境变量中配置；前端模块只传递业务 id 与
 * 用户可见内容，不引入 ``VITE_*`` 形式的秘密配置到浏览器。
 */

/** 与 Django ``ConversationMessage.Role`` 取值一致，便于直接映射 API 响应 */
export type ConversationRole = 'user' | 'assistant' | 'system'
