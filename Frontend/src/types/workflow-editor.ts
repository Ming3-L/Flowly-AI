// ─────────────────────────────────────────────────────────────────────────────
// Workflow Editor Types — Phase 4 Visual Editor
// ─────────────────────────────────────────────────────────────────────────────

export type EditorNodeType = 'chat' | 'tool' | 'condition' | 'human_approval' | 'parallel'

export interface EditorNodePort {
  id: string
  label: string
  type: 'source' | 'target'
  position: 'top' | 'bottom' | 'left' | 'right'
}

export interface EditorNodeConfig {
  // chat
  systemPrompt?: string
  model?: string

  // tool
  toolName?: 'query_database' | 'call_external_api' | 'send_notification'
  toolParams?: Record<string, any>

  // condition
  conditionExpression?: string

  // human_approval
  approvalQuestion?: string

  // parallel
  parallelBranches?: string[]
}

export interface EditorNode {
  id: string
  type: EditorNodeType
  label: string
  x: number
  y: number
  width: number
  height: number
  ports: EditorNodePort[]
  config: EditorNodeConfig
  style?: {
    color?: string
    icon?: string
  }
}

export interface EditorEdge {
  id: string
  sourceNodeId: string
  sourcePortId: string
  targetNodeId: string
  targetPortId: string
  label?: string
  animated?: boolean
}

export interface WorkflowDefinition {
  version: '1.0'
  nodes: EditorNode[]
  edges: EditorEdge[]
}

export interface WorkflowDefinitionExport {
  name: string
  description: string
  definition: WorkflowDefinition
}

// Node type metadata for palette
export const NODE_TYPE_META: Record<EditorNodeType, {
  label: string
  color: string
  icon: string
  description: string
  defaultConfig: EditorNodeConfig
  ports: EditorNodePort[]
}> = {
  chat: {
    label: '对话',
    color: '#000000',
    icon: 'ChatDotRound',
    description: 'AI 对话交互节点',
    defaultConfig: {
      systemPrompt: 'You are a helpful assistant.',
      model: 'gpt-4o',
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'out', label: 'Out', type: 'source', position: 'right' },
    ],
  },
  tool: {
    label: '工具',
    color: '#666666',
    icon: 'Tools',
    description: '执行工具（数据库、API、通知）',
    defaultConfig: {
      toolName: 'query_database',
      toolParams: {},
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'out', label: 'Out', type: 'source', position: 'right' },
    ],
  },
  condition: {
    label: '条件',
    color: '#999999',
    icon: 'Connection',
    description: '基于条件分支',
    defaultConfig: {
      conditionExpression: '',
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'true', label: 'True', type: 'source', position: 'right' },
      { id: 'false', label: 'False', type: 'source', position: 'bottom' },
    ],
  },
  human_approval: {
    label: '审批',
    color: '#333333',
    icon: 'CircleCheck',
    description: '等待人工审批',
    defaultConfig: {
      approvalQuestion: 'Do you want to proceed?',
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'approved', label: 'Approved', type: 'source', position: 'right' },
      { id: 'rejected', label: 'Rejected', type: 'source', position: 'bottom' },
    ],
  },
  parallel: {
    label: '并行',
    color: '#b3b3b3',
    icon: 'CopyDocument',
    description: '并行执行多个分支',
    defaultConfig: {
      parallelBranches: ['branch_a', 'branch_b'],
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'out', label: 'Out', type: 'source', position: 'right' },
    ],
  },
}
