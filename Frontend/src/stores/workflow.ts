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
import { buildWorkflowWebSocketUrl } from '@/utils/workflowWs'
import type {
  Workflow,
  WorkflowStatus,
  RunWorkflowRequest,
  RunWorkflowResponse,
  RunCanvasNodeRequest,
  RunCanvasNodeResponse,
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
  return buildWorkflowWebSocketUrl(threadId)
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
  const nodeTimeline = computed(() =>
    Array.from(nodeStates.value.values()).sort((a, b) => {
      const ta = a.started_at instanceof Date ? a.started_at.getTime() : 0
      const tb = b.started_at instanceof Date ? b.started_at.getTime() : 0
      return ta - tb
    })
  )

  // ── Actions ───────────────────────────────────────────────────────────────

  /**
   * Load the list of available workflows from the backend.
   */
  async function fetchWorkflows() {
    isLoading.value = true
    try {
      const res = await api.get('/workflows/')
      const data = res.data as any
      // Backend returns { total, items }, but some views expect plain array.
      const items = Array.isArray(data) ? data : (data?.items ?? [])
      workflows.value = Array.isArray(items) ? items : []
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

  function _mapMessageRole(role: string): ChatMessage['role'] {
    const r = String(role || '').toLowerCase()
    if (r === 'human' || r === 'user') return 'user'
    if (r === 'ai' || r === 'assistant') return 'assistant'
    if (r === 'tool') return 'tool'
    if (r === 'system') return 'system'
    return 'assistant'
  }

  function _hydrateFromState(st: WorkflowStateResponse) {
    const meta = (st?.metadata ?? {}) as Record<string, any>

    // 基础状态
    workflowStatus.value = (st?.status as WorkflowStatus) ?? 'pending'
    executionId.value = typeof meta.execution_id === 'number' ? meta.execution_id : null

    // 消息回放
    const rawMsgs = Array.isArray(st?.messages) ? st.messages : []
    messages.value = rawMsgs
      .map((m: any) => {
        const role = _mapMessageRole(m?.role ?? m?.type)
        const content = String(m?.content ?? '').trim()
        if (!content) return null
        return {
          id: makeId(),
          role,
          content,
          timestamp: new Date(),
        } as ChatMessage
      })
      .filter(Boolean) as ChatMessage[]

    // 节点时间线（复用现有映射逻辑）
    nodeStates.value.clear()
    const steps = meta?.node_steps as Array<Record<string, any>> | undefined
    if (steps?.length) {
      for (const s of steps) {
        const key = String(s.node_key ?? '')
        if (!key) continue
        nodeStates.value.set(key, {
          node: key,
          title: s.display_title,
          activity: s.activity,
          node_type: s.node_kind,
          model_route: s.model_route,
          status: _mapStepStatus(String(s.status ?? '')),
          started_at: s.started_at ? new Date(s.started_at) : undefined,
          finished_at: s.finished_at ? new Date(s.finished_at) : undefined,
        })
      }
    }
  }

  /**
   * 从 URL/历史进入：加载 thread 的历史对话与节点状态，并在需要时重连 WS。
   */
  async function loadThread(thread_id: string) {
    const id = String(thread_id || '').trim()
    if (!id) return

    _cleanupWebSocket()
    resetExecutionState()

    threadId.value = id
    isRunning.value = false
    errorMessage.value = null

    const st = await fetchThreadState(id)
    if (!st) return

    _hydrateFromState(st)

    // 尝试同步当前工作流（用于标题/下拉默认值）
    const meta = (st.metadata ?? {}) as Record<string, any>
    const wfId = Number(meta.workflow_id)
    if (!isNaN(wfId)) {
      currentWorkflow.value = workflows.value.find((w) => w.id === wfId) ?? currentWorkflow.value
    }

    // 若仍在运行/等待审批，则连接 WS 获取后续事件
    if (workflowStatus.value === 'running' || workflowStatus.value === 'pending') {
      isRunning.value = workflowStatus.value === 'running'
      _connectWebSocket(id)
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
      const body: Record<string, unknown> = {
        workflow_id: payload.workflow_id,
        query: payload.query,
      }
      if (payload.context !== undefined) body.context = payload.context
      if (payload.client_node_id) body.client_node_id = payload.client_node_id
      if (payload.model_name) body.model_name = payload.model_name
      if (payload.parallel_branches?.length) body.parallel_branches = payload.parallel_branches

      const res = await api.post<RunWorkflowResponse>('/workflows/run', body)
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
   * 串联执行画布工作流（POST /workflows/canvas/run），并通过 WS 接收节点事件。
   */
  async function startCanvasWorkflow(payload: {
    workflow_id: number
    query: string
    context?: Record<string, unknown>
    entry_node_id?: string
    initial_inputs?: Record<string, any>
    thread_id?: string
    client_node_id?: string
  }) {
    _cleanupWebSocket()
    resetExecutionState()

    isRunning.value = true
    errorMessage.value = null

    try {
      const res = await api.post<RunWorkflowResponse>('/workflows/canvas/run', {
        workflow_id: payload.workflow_id,
        thread_id: payload.thread_id ?? '',
        entry_node_id: payload.entry_node_id ?? '',
        initial_inputs: payload.initial_inputs ?? {},
        query: payload.query,
        context: payload.context ?? {},
      })

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
      errorMessage.value =
        err?.response?.data?.detail ??
        err?.response?.data?.message ??
        err.message ??
        'Failed to start canvas workflow'
      isRunning.value = false
    }
  }

  /**
   * 同步执行单个画布节点（计费带 client_node_id，不经 WebSocket）。
   */
  async function runCanvasNode(
    payload: RunCanvasNodeRequest
  ): Promise<RunCanvasNodeResponse | null> {
    errorMessage.value = null
    try {
      const res = await api.post<RunCanvasNodeResponse>('/workflows/canvas-node/run', {
        workflow_id: payload.workflow_id,
        client_node_id: payload.client_node_id,
        node_type: payload.node_type,
        config: payload.config ?? {},
        inputs: payload.inputs ?? {},
      })
      return res.data
    } catch (err: any) {
      errorMessage.value =
        err?.response?.data?.detail ?? err?.message ?? '画布节点调试请求失败'
      return null
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
  function _mapStepStatus(s: string): WorkflowNodeState['status'] {
    if (s === 'completed') return 'completed'
    if (s === 'failed') return 'failed'
    if (s === 'running') return 'running'
    return 'idle'
  }

  async function _hydrateNodeStatesFromServer(id: string) {
    const st = await fetchThreadState(id)
    const meta = st?.metadata as Record<string, any> | undefined
    const steps = meta?.node_steps as Array<Record<string, any>> | undefined
    if (steps?.length) {
      for (const s of steps) {
        const key = String(s.node_key ?? '')
        if (!key) continue
        nodeStates.value.set(key, {
          node: key,
          title: s.display_title,
          activity: s.activity,
          node_type: s.node_kind,
          model_route: s.model_route,
          status: _mapStepStatus(String(s.status ?? '')),
          started_at: s.started_at ? new Date(s.started_at) : undefined,
          finished_at: s.finished_at ? new Date(s.finished_at) : undefined,
        })
      }
    }
    const live = meta?.execution_live as Record<string, any> | undefined
    if (live?.node && isRunning.value) {
      const key = String(live.node)
      nodeStates.value.set(key, {
        node: key,
        title: live.title,
        activity: live.activity,
        model_route: live.model_route,
        node_type: live.node_type,
        status: 'running',
        started_at: new Date(),
      })
    }
  }

  function _connectWebSocket(id: string) {
    _wsShouldReconnect = true
    const url = buildWSUrl(id)

    _ws = new WebSocket(url)

    _ws.onopen = () => {
      console.debug(`[WS] Connected to thread ${id}`)
      _wsShouldReconnect = true
      void _hydrateNodeStatesFromServer(id)
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
        _onNodeStart({
          node: event.node,
          title: event.title ?? event.display_title,
          activity: event.activity,
          node_type: event.node_type,
          model_route: event.model_route,
        })
        break

      case 'node_end':
        _onNodeEnd(event.node, event.status, {
          activity: event.activity,
          title: event.title ?? event.display_title,
          model_route: event.model_route,
        })
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

  function _onNodeStart(payload: {
    node: string
    title?: string
    activity?: string
    node_type?: string
    model_route?: string
  }) {
    const { node, title, activity, node_type, model_route } = payload
    activeNode.value = node
    workflowStatus.value = 'running'
    nodeStates.value.set(node, {
      node,
      status: 'running',
      started_at: new Date(),
      title,
      activity,
      node_type,
      model_route,
    })
  }

  function _onNodeEnd(
    node: string,
    status: string,
    extra?: { activity?: string; title?: string; model_route?: string }
  ) {
    const existing = nodeStates.value.get(node)
    nodeStates.value.set(node, {
      node,
      status: status === 'completed' ? 'completed' : 'failed',
      started_at: existing?.started_at,
      finished_at: new Date(),
      title: extra?.title ?? existing?.title,
      activity: extra?.activity ?? existing?.activity,
      node_type: existing?.node_type,
      model_route: extra?.model_route ?? existing?.model_route,
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

    // 画布跑完时 ``result.response`` 通常等于最后一个节点已在 ``node_end`` 里刷入的对话内容，避免重复一条。
    if (status === 'completed' && result?.response) {
      const resp = String(result.response).trim()
      const last = messages.value.length ? messages.value[messages.value.length - 1] : null
      const dup =
        last?.role === 'assistant' && String(last.content).trim() === resp
      if (resp && !dup) {
        _appendMessage('assistant', result.response, 'format_response')
      }
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
    loadThread,
    startWorkflow,
    startCanvasWorkflow,
    runCanvasNode,
    resumeWorkflow,
    resetExecutionState,
  }
})
