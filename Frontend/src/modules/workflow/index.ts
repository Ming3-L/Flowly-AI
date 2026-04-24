/**
 * 工作流领域 —— 前端模块化入口（预留）
 *
 * 职责划分建议
 * ------------
 * - **节点类型常量**：与后端 ``WorkflowGraphNode.node_type``、
 *   ``workflow_nodes.registry.NodeTypeId`` 使用同一套字符串，避免前后端漂移。
 * - **DTO / 校验**：后续可在此导出 Zod schema 或 TypeScript 接口，对应保存画布时
 *   POST 给后端的 nodes/edges 数组结构（与 ``WorkflowGraphRepository.replace_graph`` 对齐）。
 * - **API 客户端**：封装「加载图」「保存图到 MySQL + definition 双写」等函数，
 *   不要在前端硬编码任何 API Key。
 *
 * 与 Vue Flow 的关系
 * ------------------
 * Vue Flow 的 ``node.id`` / ``edge.id`` 应分别映射为后端的 ``client_node_id``、
 * ``client_edge_id``；坐标使用 ``position`` 对象写入 ``position_x`` / ``position_y``。
 * 已实现入口：``WorkflowRunner`` 可选填「画布节点 ID」随 ``POST /workflows/run`` 提交；
 * 编辑器工具栏「调试节点」随 ``POST /workflows/canvas-node/run`` 提交当前 ``node.id``。
 */

/** 内置节点类型字面量联合；新增类型时需与后端枚举同步 */
export const WORKFLOW_NODE_TYPES = [
  'text',
  'audio',
  'image',
  'video',
  'ai_chat',
  'custom',
] as const

/** 取自 ``WORKFLOW_NODE_TYPES`` 的单个类型字符串 */
export type WorkflowNodeTypeId = (typeof WORKFLOW_NODE_TYPES)[number]
