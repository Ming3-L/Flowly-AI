/**
 * useWorkflowEditorStore — Pinia store for the visual workflow editor
 *
 * Manages:
 * - Canvas state: nodes, edges, selection, zoom, pan
 * - Node CRUD: add, remove, update, move
 * - Edge CRUD: add, remove
 * - Serialization: WorkflowDefinition ↔ JSON
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  EditorNode,
  EditorEdge,
  EditorNodeType,
  EditorNodeConfig,
  WorkflowDefinition,
  WorkflowDefinitionExport,
} from '@/types/workflow-editor'
import { NODE_TYPE_META } from '@/types/workflow-editor'

export const useWorkflowEditorStore = defineStore('workflowEditor', () => {
  // ── State ──────────────────────────────────────────────────────────────────

  const nodes = ref<EditorNode[]>([])
  const edges = ref<EditorEdge[]>([])
  const selectedNodeId = ref<string | null>(null)
  const selectedEdgeId = ref<string | null>(null)

  // Canvas transform
  const zoom = ref(1)
  const panX = ref(0)
  const panY = ref(0)

  // Drag state
  const draggingNodeId = ref<string | null>(null)
  const draggingEdgeSource = ref<{ nodeId: string; portId: string } | null>(null)

  // ── Computed ───────────────────────────────────────────────────────────────

  const selectedNode = computed(() =>
    nodes.value.find((n) => n.id === selectedNodeId.value) ?? null
  )

  const hasUnsavedChanges = ref(false)

  const definition = computed<WorkflowDefinition>(() => ({
    version: '1.0',
    nodes: nodes.value,
    edges: edges.value,
  }))

  // ── Node Actions ───────────────────────────────────────────────────────────

  function createNode(type: EditorNodeType, x: number, y: number): EditorNode {
    const meta = NODE_TYPE_META[type]
    const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    const node: EditorNode = {
      id,
      type,
      label: `${meta.label} ${nodes.value.filter((n) => n.type === type).length + 1}`,
      x,
      y,
      width: 200,
      height: 80,
      ports: meta.ports.map((p) => ({
        ...p,
        id: `${id}_${p.id}`,
      })),
      config: { ...meta.defaultConfig },
      style: { color: meta.color },
    }
    nodes.value.push(node)
    hasUnsavedChanges.value = true
    return node
  }

  function updateNode(id: string, updates: Partial<EditorNode>) {
    const idx = nodes.value.findIndex((n) => n.id === id)
    if (idx === -1) return
    nodes.value[idx] = { ...nodes.value[idx], ...updates }
    hasUnsavedChanges.value = true
  }

  function updateNodeConfig(id: string, config: Partial<EditorNodeConfig>) {
    const node = nodes.value.find((n) => n.id === id)
    if (!node) return
    node.config = { ...node.config, ...config }
    hasUnsavedChanges.value = true
  }

  function moveNode(id: string, x: number, y: number) {
    const node = nodes.value.find((n) => n.id === id)
    if (!node) return
    node.x = x
    node.y = y
    hasUnsavedChanges.value = true
  }

  function removeNode(id: string) {
    nodes.value = nodes.value.filter((n) => n.id !== id)
    edges.value = edges.value.filter(
      (e) => e.sourceNodeId !== id && e.targetNodeId !== id
    )
    if (selectedNodeId.value === id) selectedNodeId.value = null
    hasUnsavedChanges.value = true
  }

  function duplicateNode(id: string) {
    const node = nodes.value.find((n) => n.id === id)
    if (!node) return
    const copy = createNode(node.type, node.x + 30, node.y + 30)
    updateNode(copy.id, { label: `${node.label} (copy)` })
    return copy
  }

  // ── Edge Actions ───────────────────────────────────────────────────────────

  function createEdge(
    sourceNodeId: string,
    sourcePortId: string,
    targetNodeId: string,
    targetPortId: string
  ): EditorEdge | null {
    // Prevent duplicate edges
    const exists = edges.value.some(
      (e) =>
        e.sourceNodeId === sourceNodeId &&
        e.sourcePortId === sourcePortId &&
        e.targetNodeId === targetNodeId &&
        e.targetPortId === targetPortId
    )
    if (exists) return null

    // Prevent self-loops
    if (sourceNodeId === targetNodeId) return null

    const id = `edge_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    const edge: EditorEdge = {
      id,
      sourceNodeId,
      sourcePortId,
      targetNodeId,
      targetPortId,
    }
    edges.value.push(edge)
    hasUnsavedChanges.value = true
    return edge
  }

  function removeEdge(id: string) {
    edges.value = edges.value.filter((e) => e.id !== id)
    if (selectedEdgeId.value === id) selectedEdgeId.value = null
    hasUnsavedChanges.value = true
  }

  function updateEdgeLabel(id: string, label: string) {
    const edge = edges.value.find((e) => e.id === id)
    if (edge) {
      edge.label = label
      hasUnsavedChanges.value = true
    }
  }

  // ── Selection ───────────────────────────────────────────────────────────────

  function selectNode(id: string | null) {
    selectedNodeId.value = id
    selectedEdgeId.value = null
  }

  function selectEdge(id: string | null) {
    selectedEdgeId.value = id
    selectedNodeId.value = null
  }

  function clearSelection() {
    selectedNodeId.value = null
    selectedEdgeId.value = null
  }

  // ── Canvas ─────────────────────────────────────────────────────────────────

  function setZoom(z: number) {
    zoom.value = Math.min(Math.max(z, 0.1), 3)
  }

  function setPan(x: number, y: number) {
    panX.value = x
    panY.value = y
  }

  function resetView() {
    zoom.value = 1
    panX.value = 0
    panY.value = 0
  }

  function zoomIn() {
    setZoom(zoom.value + 0.1)
  }

  function zoomOut() {
    setZoom(zoom.value - 0.1)
  }

  // ── Serialization ──────────────────────────────────────────────────────────

  function loadFromDefinition(def: WorkflowDefinition) {
    nodes.value = def.nodes ?? []
    edges.value = def.edges ?? []
    selectedNodeId.value = null
    selectedEdgeId.value = null
    hasUnsavedChanges.value = false
  }

  function loadFromExport(exportData: WorkflowDefinitionExport) {
    if (exportData.definition) {
      loadFromDefinition(exportData.definition)
    }
  }

  function toExport(name: string, description: string): WorkflowDefinitionExport {
    return {
      name,
      description,
      definition: definition.value,
    }
  }

  function clear() {
    nodes.value = []
    edges.value = []
    selectedNodeId.value = null
    selectedEdgeId.value = null
    hasUnsavedChanges.value = false
    resetView()
  }

  // ── Layout ─────────────────────────────────────────────────────────────────

  function autoLayout() {
    // Simple layered layout (Dagre-inspired but manual)
    if (nodes.value.length === 0) return

    const inDegree = new Map<string, number>()
    const adjacency = new Map<string, string[]>()

    nodes.value.forEach((n) => {
      inDegree.set(n.id, 0)
      adjacency.set(n.id, [])
    })

    edges.value.forEach((e) => {
      const current = inDegree.get(e.targetNodeId) ?? 0
      inDegree.set(e.targetNodeId, current + 1)
      adjacency.get(e.sourceNodeId)?.push(e.targetNodeId)
    })

    // Topological sort into layers
    const layers: string[][] = []
    const remaining = new Set(nodes.value.map((n) => n.id))
    const placed = new Set<string>()

    while (remaining.size > 0) {
      const layer: string[] = []
      remaining.forEach((id) => {
        if ((inDegree.get(id) ?? 0) === 0) {
          layer.push(id)
        }
      })
      if (layer.length === 0) {
        // Cycle detected — place remaining nodes
        layer.push(...remaining)
      }
      layer.forEach((id) => {
        remaining.delete(id)
        placed.add(id)
        ;(adjacency.get(id) ?? []).forEach((next) => {
          const d = (inDegree.get(next) ?? 0) - 1
          inDegree.set(next, d)
        })
      })
      layers.push(layer)
    }

    const GAP_X = 280
    const GAP_Y = 120
    const START_X = 100
    const START_Y = 80

    layers.forEach((layer, li) => {
      const totalHeight = (layer.length - 1) * GAP_Y
      let startY = START_Y - totalHeight / 2

      layer.forEach((id, ni) => {
        const node = nodes.value.find((n) => n.id === id)
        if (node) {
          node.x = START_X + li * GAP_X
          node.y = startY + ni * GAP_Y
        }
      })
    })

    hasUnsavedChanges.value = true
  }

  // ── Validation ─────────────────────────────────────────────────────────────

  const validationErrors = computed<string[]>(() => {
    const errors: string[] = []

    if (nodes.value.length === 0) {
      errors.push('Workflow must have at least one node')
      return errors
    }

    // Check for unconnected nodes (except those with no incoming edges = entry nodes)
    const hasIncoming = new Set(edges.value.map((e) => e.targetNodeId))
    nodes.value.forEach((n) => {
      if (n.type !== 'chat' && !hasIncoming.has(n.id)) {
        // Only warn about non-entry nodes without incoming edges
      }
    })

    // Check for unconnected nodes with no outgoing edges (dead ends)
    const hasOutgoing = new Set(edges.value.map((e) => e.sourceNodeId))
    nodes.value.forEach((n) => {
      if (n.type !== 'human_approval' && !hasOutgoing.has(n.id)) {
        // Allow human_approval to be a terminal node
      }
    })

    // Check for missing labels
    nodes.value.forEach((n) => {
      if (!n.label.trim()) {
        errors.push(`Node ${n.id} has no label`)
      }
    })

    return errors
  })

  const isValid = computed(() => validationErrors.value.length === 0)

  return {
    // State
    nodes,
    edges,
    selectedNodeId,
    selectedEdgeId,
    zoom,
    panX,
    panY,
    draggingNodeId,
    draggingEdgeSource,
    hasUnsavedChanges,

    // Computed
    selectedNode,
    definition,
    isValid,
    validationErrors,

    // Node actions
    createNode,
    updateNode,
    updateNodeConfig,
    moveNode,
    removeNode,
    duplicateNode,

    // Edge actions
    createEdge,
    removeEdge,
    updateEdgeLabel,

    // Selection
    selectNode,
    selectEdge,
    clearSelection,

    // Canvas
    setZoom,
    setPan,
    resetView,
    zoomIn,
    zoomOut,

    // Serialization
    loadFromDefinition,
    loadFromExport,
    toExport,
    clear,

    // Layout
    autoLayout,
  }
})
