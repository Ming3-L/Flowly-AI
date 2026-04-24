// ─────────────────────────────────────────────────────────────────────────────
// Workflow Editor Types — Phase 4 Visual Editor
// ─────────────────────────────────────────────────────────────────────────────

export type EditorNodeType =
  | 'chat'
  | 'tool'
  | 'condition'
  | 'human_approval'
  | 'parallel'
  | 'text'
  | 'image'
  | 'audio'
  | 'video'

export interface EditorNodePort {
  id: string
  label: string
  type: 'source' | 'target'
  position: 'top' | 'bottom' | 'left' | 'right'
}

export interface EditorNodeConfig {
  // chat
  systemPrompt?: string
  /** 项目内置 AI 模型预设 key，与 GET /api/ai/models 的 models[].key 一致 */
  modelKey?: string
  /** @deprecated 仅兼容旧工作流；新节点请使用 modelKey */
  provider?: string
  /** @deprecated 仅兼容旧工作流；新节点请使用 modelKey */
  model?: string
  temperature?: number
  max_tokens?: number

  // tool
  toolName?: 'query_database' | 'call_external_api' | 'send_notification'
  toolParams?: Record<string, any>

  // condition
  conditionExpression?: string

  // human_approval
  approvalQuestion?: string

  // parallel
  parallelBranches?: string[]

  // text
  processMode?: 'llm' | 'template'
  prompt?: string

  // image
  captionPrompt?: string
  image_url?: string

  // audio
  audio_url?: string

  // video
  video_url?: string
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
    description: 'AI 对话交互节点（默认与文本/图片等一致：豆包，模型走 DOUBAO_ARK_MODEL）',
    defaultConfig: {
      systemPrompt: 'You are a helpful assistant.',
      modelKey: 'doubao-default',
      temperature: 0.7,
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
  text: {
    label: '文本',
    color: '#111111',
    icon: 'Document',
    description: 'AI 文本处理（摘要、改写等）或仅模板拼接',
    defaultConfig: {
      processMode: 'llm',
      systemPrompt: '你是助手。',
      prompt: '请对下方文本进行摘要。',
      modelKey: 'doubao-default',
      temperature: 0.7,
      max_tokens: 1024,
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'out', label: 'Out', type: 'source', position: 'right' },
    ],
  },
  image: {
    label: '图片',
    color: '#444444',
    icon: 'PictureFilled',
    description: '多模态图片理解（URL + 提问），模型与对话节点一致配置',
    defaultConfig: {
      captionPrompt: '请简要描述这张图片的主要内容。',
      modelKey: 'doubao-default',
      temperature: 0.7,
      max_tokens: 1024,
      image_url: '',
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'out', label: 'Out', type: 'source', position: 'right' },
    ],
  },
  audio: {
    label: '音频',
    color: '#777777',
    icon: 'Microphone',
    description: 'Whisper 转写（需 OPENAI_API_KEY）+ 大模型摘要；或直接处理转写文本',
    defaultConfig: {
      systemPrompt: '你是助手。根据用户提供的音频转写文本，输出简洁的中文要点列表。',
      modelKey: 'doubao-default',
      temperature: 0.7,
      max_tokens: 1024,
      audio_url: '',
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'out', label: 'Out', type: 'source', position: 'right' },
    ],
  },
  video: {
    label: '视频',
    color: '#222222',
    icon: 'VideoCamera',
    description: '对视频相关文案/分镜说明做结构化摘要（视频 URL 仅作元数据）',
    defaultConfig: {
      systemPrompt: '你是助手。根据用户提供的视频相关文字说明，输出结构化摘要。',
      modelKey: 'doubao-default',
      temperature: 0.7,
      max_tokens: 2048,
      video_url: '',
    },
    ports: [
      { id: 'in', label: 'In', type: 'target', position: 'left' },
      { id: 'out', label: 'Out', type: 'source', position: 'right' },
    ],
  },
}
