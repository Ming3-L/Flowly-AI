/**
 * useWorkflowStore — Pinia store for workflow management
 *
 * Handles:
 * - Fetching available workflows (list)
 * - Starting a new execution (POST /run)
 * - WebSocket streaming for real-time events
 * - Maintaining chat message history
 * - Tracking node-level execution status
 * - Human-in-the-loop resume
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/utils/api'
import type {
  Workflow,
  WorkflowStatus,
  RunWorkflowRequest,
  RunWorkflowResponse,
  WorkflowStateResponse,
  ResumeWorkflowRequest,
  ResumeWorkflowResponse,
  ChatMessage,
  WorkflowNodeState,
  SSEEvent,
  ExecutionHistoryItem,
} from '@/types'

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

let _messageCounter = 0
function makeId() {
  return `msg_${++_messageCounter}_${Date.now()}`
}

function buildWSUrl(threadId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/workflow/${threadId}/`
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Definition
// ─────────────────────────────────────────────────────────────────────────────

export const useWorkflowStore = defineStore('workflow', () => {
  // ── State ──────────────────────────────────────────────────────────────────

  /** List of all registered workflows. */
  const workflows = ref<Workflow[]>([])

  /** Currently selected / active workflow. */
  const currentWorkflow = ref<Workflow | null>(null)

  /** Whether the workflow list is being fetched. */
  const isLoading = ref(false)

  /** Whether an execution is currently running. */
  const isRunning = ref(false)

  /** UUID of the active thread. */
  const threadId = ref<string | null>(null)

  /** Execution ID from the backend. */
  const executionId = ref<number | null>(null)

  /** Overall workflow status. */
  const workflowStatus = ref<WorkflowStatus>('pending')

  /** Chat messages for the current thread. */
  const messages = ref<ChatMessage[]>([])

  /** Per-node execution state map, keyed by node name. */
  const nodeStates = ref<Map<string, WorkflowNodeState>>(new Map())

  /** The node currently emitting tokens (for streaming highlight). */
  const activeNode = ref<string | null>(null)

  /** Human-in-the-loop: whether workflow is awaiting approval. */
  const pendingApproval = ref(false)
  const pendingQuestion = ref('')

  /** Accumulated streaming token (displayed while streaming). */
  const streamingContent = ref('')

  /** Execution history for the sidebar. */
  const history = ref<ExecutionHistoryItem[]>([])

  /** Error message if last run failed. */
  const errorMessage = ref<string | null>(null)

  /** WebSocket instance (managed by the store). */
  let _ws: WebSocket | null = null
  let _wsReconnectTimer: ReturnType<typeof setTimeout> | null = null
  let _wsShouldReconnect = false

  // ── Computed ───────────────────────────────────────────────────────────────

  const hasActiveThread = computed(() => !!threadId.value)

  const isFinished = computed(
    () => workflowStatus.value === 'completed' || workflowStatus.value === 'failed'
  )

  /** Ordered list of node states for the timeline display. */
  const nodeTimeline = computed(() => Array.from(nodeStates.value.values()))

  // ── Actions ───────────────────────────────────────────────────────────────

  /**
   * Load the list of available workflows from the backend.
   */
  async function fetchWorkflows() {
    isLoading.value = true
    try {
      const res = await api.get('/workflows/')
      workflows.value = res.data.items ?? []
    } catch {
      workflows.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch detailed state for a given thread.
   */
  async function fetchThreadState(id: string): Promise<WorkflowStateResponse | null> {
    try {
      const res = await api.get<WorkflowStateResponse>(`/workflows/${id}/state`)
      return res.data
    } catch {
      return null
    }
  }

  /**
   * Start a new workflow execution.
   * Resets state, calls POST /run, then opens the WebSocket stream.
   */
  async function startWorkflow(payload: RunWorkflowRequest) {
    _cleanupWebSocket()
    resetExecutionState()

    isRunning.value = true
    errorMessage.value = null

    try {
      const res = await api.post<RunWorkflowResponse>('/workflows/run', payload)
      const { thread_id, status, execution_id } = res.data

      threadId.value = thread_id
      executionId.value = execution_id
      workflowStatus.value = status

      currentWorkflow.value =
        workflows.value.find((w) => w.id === payload.workflow_id) ?? null

      messages.value.push({
        id: makeId(),
        role: 'user',
        content: payload.query,
        timestamp: new Date(),
      })

      _connectWebSocket(thread_id)

      history.value.unshift({
        execution_id: execution_id ?? 0,
        thread_id,
        started_at: new Date(),
        status,
        query: payload.query,
      })
    } catch (err: any) {
      errorMessage.value = err?.response?.data?.detail ?? err.message ?? 'Failed to start workflow'
      isRunning.value = false
    }
  }

  /**
   * Resume a paused (pending_approval) workflow.
   */
  async function resumeWorkflow(payload: ResumeWorkflowRequest) {
    if (!threadId.value) return

    pendingApproval.value = false
    pendingQuestion.value = ''

    try {
      const res = await api.post<ResumeWorkflowResponse>(
        `/workflows/${threadId.value}/resume`,
        payload
      )
      workflowStatus.value = res.data.status
    } catch (err: any) {
      errorMessage.value = err?.response?.data?.detail ?? 'Failed to resume workflow'
    }
  }

  /**
   * Connect to the WebSocket for the given thread.
   */
  function _connectWebSocket(id: string) {
    _wsShouldReconnect = true
    const url = buildWSUrl(id)

    _ws = new WebSocket(url)

    _ws.onopen = () => {
      console.debug(`[WS] Connected to thread ${id}`)
      _wsShouldReconnect = true
    }

    _ws.onmessage = (event) => {
      let data: SSEEvent
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }
      _handleEvent(data)
    }

    _ws.onerror = (event) => {
      console.warn('[WS] Connection error', event)
    }

    _ws.onclose = () => {
      console.debug('[WS] Connection closed')
      if (_wsShouldReconnect && !isFinished.value) {
        // Attempt reconnect after 2 seconds
        _wsReconnectTimer = setTimeout(() => {
          if (_wsShouldReconnect && !isFinished.value && threadId.value) {
            _connectWebSocket(threadId.value)
          }
        }, 2000)
      }
    }
  }

  /**
   * Dispatch incoming WebSocket events to the appropriate handler.
   */
  function _handleEvent(event: SSEEvent) {
    switch (event.event_type) {
      case 'connected':
        break

      case 'node_start':
        _onNodeStart(event.node)
        break

      case 'node_end':
        _onNodeEnd(event.node, event.status)
        break

      case 'token':
        _onToken(event.content, event.node)
        break

      case 'tool_call':
        _onToolCall(event.tool, event.params, event.node)
        break

      case 'tool_result':
        _onToolResult(event.content, event.node)
        break

      case 'workflow_end':
        _onWorkflowEnd(event.status, event.result)
        break

      case 'workflow_error':
        _onWorkflowError(event.error)
        break

      case 'workflow_resumed':
        _onWorkflowResumed(event.approved, event.user_input)
        break

      case 'pending_approval':
        _onPendingApproval(event.question, event.reasoning, event.node)
        break

      case 'message':
      default:
        if (event.content) {
          _appendMessage('assistant', event.content, event.node)
        }
        break
    }
  }

  // ── Event Handlers ────────────────────────────────────────────────────────

  function _onNodeStart(node: string) {
    activeNode.value = node
    workflowStatus.value = 'running'
    nodeStates.value.set(node, {
      node,
      status: 'running',
      started_at: new Date(),
    })
  }

  function _onNodeEnd(node: string, status: string) {
    const existing = nodeStates.value.get(node)
    nodeStates.value.set(node, {
      node,
      status: status === 'completed' ? 'completed' : 'failed',
      started_at: existing?.started_at,
      finished_at: new Date(),
    })
    if (activeNode.value === node) {
      if (streamingContent.value) {
        _appendMessage('assistant', streamingContent.value, node)
        streamingContent.value = ''
      }
      activeNode.value = null
    }
  }

  function _onToken(content: string, node: string) {
    activeNode.value = node
    streamingContent.value += content
  }

  function _onToolCall(tool: string, params: Record<string, any>, node: string) {
    _appendMessage(
      'system',
      `Calling tool \`${tool}\` with params: ${JSON.stringify(params)}`,
      node
    )
  }

  function _onToolResult(content: string, node: string) {
    _appendMessage('tool', content, node)
  }

  function _onWorkflowEnd(status: string, result?: Record<string, any>) {
    _flushStreaming()
    workflowStatus.value = status as WorkflowStatus
    isRunning.value = false
    activeNode.value = null

    if (status === 'completed' && result?.response) {
      _appendMessage('assistant', result.response, 'format_response')
    }

    const entry = history.value.find((h) => h.thread_id === threadId.value)
    if (entry) entry.status = status as WorkflowStatus

    _cleanupWebSocket()
  }

  function _onWorkflowError(error: string) {
    workflowStatus.value = 'failed'
    isRunning.value = false
    errorMessage.value = error
    _appendMessage('system', `Error: ${error}`, 'error')
    _cleanupWebSocket()
  }

  function _onWorkflowResumed(approved: boolean, userInput?: string) {
    _appendMessage(
      'user',
      approved ? `Approved: ${userInput}` : `Rejected: ${userInput}`,
      'resume'
    )
    workflowStatus.value = 'running'
    pendingApproval.value = false
    pendingQuestion.value = ''
  }

  function _onPendingApproval(question: string, reasoning?: string, node?: string) {
    pendingApproval.value = true
    pendingQuestion.value = question
    workflowStatus.value = 'pending'

    let content = question
    if (reasoning) content += `\n\n**Reasoning:** ${reasoning}`

    const msgs = messages.value
    const existing = msgs.length > 0 ? msgs[msgs.length - 1] : null
    if (existing) {
      existing.content += `\n\n${content}`
    } else {
      _appendMessage('assistant', content, node)
    }
  }

  // ── Internal Helpers ───────────────────────────────────────────────────────

  function _appendMessage(
    role: ChatMessage['role'],
    content: string,
    node?: string
  ) {
    messages.value.push({
      id: makeId(),
      role,
      content,
      timestamp: new Date(),
      node,
    })
  }

  function _flushStreaming() {
    if (streamingContent.value) {
      _appendMessage('assistant', streamingContent.value, activeNode.value ?? undefined)
      streamingContent.value = ''
    }
  }

  function _cleanupWebSocket() {
    _wsShouldReconnect = false
    if (_wsReconnectTimer !== null) {
      clearTimeout(_wsReconnectTimer)
      _wsReconnectTimer = null
    }
    if (_ws !== null) {
      _ws.close()
      _ws = null
    }
  }

  /** Reset all execution-related state (keeps workflow list). */
  function resetExecutionState() {
    threadId.value = null
    executionId.value = null
    workflowStatus.value = 'pending'
    messages.value = []
    nodeStates.value.clear()
    activeNode.value = null
    pendingApproval.value = false
    pendingQuestion.value = ''
    streamingContent.value = ''
    errorMessage.value = null
    isRunning.value = false
    _cleanupWebSocket()
  }

  return {
    // State
    workflows,
    currentWorkflow,
    isLoading,
    isRunning,
    threadId,
    executionId,
    workflowStatus,
    messages,
    nodeStates,
    activeNode,
    pendingApproval,
    pendingQuestion,
    streamingContent,
    history,
    errorMessage,

    // Computed
    hasActiveThread,
    isFinished,
    nodeTimeline,

    // Actions
    fetchWorkflows,
    fetchThreadState,
    startWorkflow,
    resumeWorkflow,
    resetExecutionState,
  }
})
