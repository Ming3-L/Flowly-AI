/**
 * vueFlowBridge — converts between @vue-flow/core types and EditorNode/EditorEdge
 *
 * Vue Flow uses { id, position, data, type } for nodes and { id, source, target, sourceHandle, targetHandle } for edges.
 * We keep EditorNode/EditorEdge as the canonical format for API serialization
 * and only convert at the boundary (store ↔ VueFlow component).
 */

import type { Node, Edge, Connection } from '@vue-flow/core'
import type { EditorNode, EditorEdge, EditorNodeType } from '@/types/workflow-editor'
import { NODE_TYPE_META } from '@/types/workflow-editor'

// ── EditorNode → VueFlow Node ─────────────────────────────────────────────────

export function editorNodeToVueFlow(node: EditorNode): Node {
  return {
    id: node.id,
    type: node.type,
    position: { x: node.x, y: node.y },
    data: {
      label: node.label,
      config: node.config,
      style: node.style,
      ports: node.ports,
    },
  }
}

// ── VueFlow Node → EditorNode ─────────────────────────────────────────────────
// Used for initial loading from API. VueFlow never mutates our data object
// directly — we keep the original EditorNode shape intact.

export function vueFlowNodeToEditor(node: Node): EditorNode {
  const meta = NODE_TYPE_META[node.type as EditorNodeType]
  return {
    id: node.id,
    type: node.type as EditorNodeType,
    label: node.data?.label ?? `${meta?.label ?? '节点'} ${node.id}`,
    x: node.position.x,
    y: node.position.y,
    width: 200,
    height: 80,
    ports: node.data?.ports ?? meta?.ports ?? [],
    config: node.data?.config ?? {},
    style: node.data?.style ?? { color: meta?.color ?? '#000000' },
  }
}

// ── EditorEdge → VueFlow Edge ─────────────────────────────────────────────────

export function editorEdgeToVueFlow(edge: EditorEdge): Edge {
  return {
    id: edge.id,
    source: edge.sourceNodeId,
    target: edge.targetNodeId,
    sourceHandle: edge.sourcePortId,
    targetHandle: edge.targetPortId,
    label: edge.label,
    animated: edge.animated,
    type: 'smoothstep',
  }
}

// ── VueFlow Connection → EditorEdge ──────────────────────────────────────────
// Converts a VueFlow Connection (emitted by @connect event) into an EditorEdge.

export function connectionToEditorEdge(connection: Connection): EditorEdge {
  return {
    id: `edge_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    sourceNodeId: connection.source,
    sourcePortId: connection.sourceHandle ?? 'out',
    targetNodeId: connection.target,
    targetPortId: connection.targetHandle ?? 'in',
  }
}

// ── Bulk conversions ─────────────────────────────────────────────────────────

export function editorNodesToVueFlow(nodes: EditorNode[]): Node[] {
  return nodes.map(editorNodeToVueFlow)
}

export function editorEdgesToVueFlow(edges: EditorEdge[]): Edge[] {
  return edges.map(editorEdgeToVueFlow)
}

export function vueFlowNodesToEditor(nodes: Node[]): EditorNode[] {
  return nodes.map(vueFlowNodeToEditor)
}

// ── VueFlow → EditorNode position sync ───────────────────────────────────────
// After VueFlow drag, we need to update x/y in our store. This reads the
// current position from a Node object and returns an updated EditorNode.

export function syncNodePosition(node: Node, editorNode: EditorNode): EditorNode {
  return {
    ...editorNode,
    x: node.position.x,
    y: node.position.y,
  }
}

// ── Create new node ──────────────────────────────────────────────────────────
// Returns an EditorNode + VueFlow Node pair for a newly dragged-from-palette node.

export function createNodePair(
  type: EditorNodeType,
  position: { x: number; y: number }
): { editor: EditorNode; vueFlow: Node } {
  const meta = NODE_TYPE_META[type]
  const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
  const editor: EditorNode = {
    id,
    type,
    label: meta.label,
    x: position.x,
    y: position.y,
    width: 200,
    height: 80,
    ports: meta.ports.map((p) => ({ ...p, id: `${id}_${p.id}` })),
    config: { ...meta.defaultConfig },
    style: { color: meta.color },
  }
  const vueFlow: Node = editorNodeToVueFlow(editor)
  return { editor, vueFlow }
}
