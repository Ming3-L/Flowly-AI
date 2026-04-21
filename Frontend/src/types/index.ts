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
  metadata: Record<string, any>
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

