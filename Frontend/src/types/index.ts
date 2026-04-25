// ─────────────────────────────────────────────────────────────────────────────
// Core Domain Types
// ─────────────────────────────────────────────────────────────────────────────

export interface Workflow {
  id: number
  name: string
  description: string
  definition: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
  /** 列表接口在管理员视角下返回，用于区分所有者 */
  owner_user_id?: number | null
  owner_username?: string
}

export interface WorkflowExecution {
  id: number
  workflow: number
  thread_id: string
  status: WorkflowStatus
  input_data: Record<string, any>
  output_data: Record<string, any>
  error_message?: string
  started_at: string
  completed_at?: string
}

export type WorkflowStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface WorkflowInput {
  query: string
  context?: Record<string, any>
}

// ─────────────────────────────────────────────────────────────────────────────
// API Request / Response Types
// ─────────────────────────────────────────────────────────────────────────────

export interface RunWorkflowRequest {
  workflow_id: number | null
  query: string
  context?: Record<string, any>
  /** 与 Vue Flow 节点 id 一致，用于 CostRecord / token 与画布对齐 */
  client_node_id?: string
  model_name?: string
  parallel_branches?: string[]
}

/** POST /workflows/canvas-node/run */
export interface RunCanvasNodeRequest {
  workflow_id: number
  client_node_id: string
  node_type: string
  config?: Record<string, any>
  inputs?: Record<string, any>
}

export interface RunCanvasNodeResponse {
  execution_id: number
  status: string
  output: Record<string, any>
  error: string | null
}

export interface RunWorkflowResponse {
  thread_id: string
  status: WorkflowStatus
  execution_id: number | null
}

export interface WorkflowStateResponse {
  thread_id: string
  status: WorkflowStatus
  messages: ChatMessage[]
  metadata: Record<string, any> & {
    node_steps?: WorkflowExecutionStepDTO[]
    execution_live?: ExecutionLiveSnapshot | null
  }
}

/** GET /workflows/:id/state 返回的已持久化步骤（与 WS 事件字段对齐） */
export interface WorkflowExecutionStepDTO {
  node_key: string
  display_title: string
  node_kind: string
  activity: string
  model_route: string
  status: string
  started_at: string | null
  finished_at: string | null
}

/** Redis 中的当前执行快照 */
export interface ExecutionLiveSnapshot {
  node: string
  title?: string
  activity?: string
  status: string
  model_route?: string
  node_type?: string
}

export interface ResumeWorkflowRequest {
  approved: boolean
  resume_input?: string
  context?: Record<string, any>
}

export interface ResumeWorkflowResponse {
  thread_id: string
  status: WorkflowStatus
  resumed: boolean
}

// ─────────────────────────────────────────────────────────────────────────────
// SSE Event Types
// ─────────────────────────────────────────────────────────────────────────────

/** Union of all possible event types emitted by the SSE stream. */
export type SSEEventType =
  | 'connected'
  | 'node_start'
  | 'node_end'
  | 'token'
  | 'tool_call'
  | 'tool_result'
  | 'workflow_end'
  | 'workflow_error'
  | 'workflow_resumed'
  | 'pending_approval'
  | 'message'
  | 'parallel_start'
  | 'parallel_branch_start'
  | 'parallel_branch_end'
  | 'parallel_end'

export interface SSEEvent {
  event_type: SSEEventType
  [key: string]: any
}

// Node lifecycle
export interface SSENodeStartEvent {
  event_type: 'node_start'
  node: string
  status: 'running'
}

export interface SSENodeEndEvent {
  event_type: 'node_end'
  node: string
  status: 'completed' | 'failed'
}

// Token streaming
export interface SSETokenEvent {
  event_type: 'token'
  content: string
  node: string
}

// Tool events
export interface SSEToolCallEvent {
  event_type: 'tool_call'
  tool: string
  params: Record<string, any>
  node: string
}

export interface SSEToolResultEvent {
  event_type: 'tool_result'
  content: string
  node: string
}

// Workflow lifecycle
export interface SSEWorkflowEndEvent {
  event_type: 'workflow_end'
  status: 'completed' | 'rejected' | 'failed'
  thread_id: string
  result?: Record<string, any>
}

export interface SSEWorkflowErrorEvent {
  event_type: 'workflow_error'
  error: string
}

export interface SSEWorkflowResumedEvent {
  event_type: 'workflow_resumed'
  approved: boolean
  user_input?: string
  status: WorkflowStatus
}

// Pending approval prompt
export interface SSEPendingApprovalEvent {
  event_type: 'pending_approval'
  question: string
  reasoning?: string
  node: string
}

// Phase 3: Parallel execution events
export interface SSEParallelStartEvent {
  event_type: 'parallel_start'
  branches: string[]
}

export interface SSEParallelBranchStartEvent {
  event_type: 'parallel_branch_start'
  branch: string
}

export interface SSEParallelBranchEndEvent {
  event_type: 'parallel_branch_end'
  branch: string
  status: string
}

export interface SSEParallelEndEvent {
  event_type: 'parallel_end'
  status: string
}

// ─────────────────────────────────────────────────────────────────────────────
// UI State Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: Date
  node?: string
}

export interface WorkflowNodeState {
  node: string
  status: 'idle' | 'running' | 'completed' | 'failed'
  started_at?: Date
  finished_at?: Date
  /** 画布节点 label 或 LangGraph 节点展示名 */
  title?: string
  /** 当前在做什么（后端生成的中文说明） */
  activity?: string
  node_type?: string
  model_route?: string
}

export interface ExecutionHistoryItem {
  execution_id: number
  thread_id: string
  started_at: Date
  status: WorkflowStatus
  query?: string
}

// Re-export editor types
export * from './workflow-editor'

