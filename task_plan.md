# Task Plan: Flowly AI — Complete Implementation

## Goal

全面完善 Flowly AI 项目，从当前的**骨架状态**（有基础结构但功能大量 stubbed）进化为**功能完整的生产级 AI 工作流系统**。

---

## Project Status Summary (as of 2026-04-20)

| Layer | Status | Notes |
|-------|--------|-------|
| **Django + Ninja API** | 100% | All routes wired to real LangGraph engine — Phase 1 complete |
| **LangGraph Workflow Engine** | 100% | Full async nodes: router, parallel_executor, tool_executor, general_assistant — Phase 1 complete |
| **Django Channels + SSE** | 100% | Consumer, SSE endpoint works, events emit real LangGraph state via WorkflowEventEmitter |
| **Vue 3 + Pinia Frontend** | 100% | ✅ Dashboard, Monitor, Runner, Detail/List, visual editor — Phase 4/5/7 done |
| **Docker + Infrastructure** | 100% | ✅ docker-compose.yml, multi-stage Dockerfiles, nginx.conf, health endpoint, deployment guide |
| **Auth/User Management** | 100% | ✅ JWT auth, login/register pages, auth guard, profile settings |
| **Unit/E2E Tests** | 100% | ✅ pytest backend tests + Playwright E2E tests |

---

## Phases

### Phase 1: Backend Core — LangGraph Real Integration
- [x] Replace simulated `_run_workflow_async` in `api.py` with real `get_workflow_graph()` calls
- [x] Implement actual LangGraph node functions: `process_query`, `execute_workflow`, `format_response`
- [x] Add LangGraph Tool nodes for: DB query, API call, notification
- [x] Wire `langgraph-checkpoint-django` — make state persist to MySQL via `DjangoCheckpointSaver`
- [x] Implement `interrupt()` for human-in-the-loop in workflow.py
- [x] Add LangSmith tracing configuration
- [x] **Deliverable:** API `/run` calls real LangGraph, state survives restarts
- **Status:** ✅ COMPLETE (verified 2026-04-20)

### Phase 2: Backend Enhancement — Auth, Users, CRUD
- [x] Add JWT authentication via `djangorestframework-simplejwt`
- [x] Create User and Profile models (extend Django User)
- [x] Add workflow CRUD API endpoints: `GET/POST/PUT/DELETE /workflows/`
- [x] Add execution history API: `GET /executions/`, `GET /executions/{id}/`
- [x] Protect all API endpoints (require auth)
- [x] Add Django admin registrations for Workflow, Thread, WorkflowExecution
- [x] **Deliverable:** Full auth-gated CRUD, admin panel usable
- **Status:** ✅ COMPLETE (auth integrated, user isolation verified, 12/12 tests passing — 2026-04-20)

### Phase 3: Backend — Parallel Nodes & Advanced LangGraph
- [x] Implement parallel content generation using LangGraph Send API
- [x] Add branching logic: `route_to_tool` conditional edge
- [x] Implement `interrupt()` + `Command(resume=True)` for approval flows
- [x] Add retry logic with tenacity for flaky LLM/tool calls
- [x] Add multi-model support (Claude, local models via Ollama)
- [x] **Deliverable:** Complex workflows with parallel branches and human approval
- **Status:** ✅ COMPLETE

### Phase 4: Frontend — Visual Workflow Editor
- **Status:** ✅ COMPLETE (verified 2026-04-20)

**Phase 4.1: WorkflowEditor.vue — Core Canvas**
- SVG canvas with pan/zoom
- Node palette (sidebar) with drag-drop node creation
- Node types: Chat, Tool, Condition, HumanApproval, Parallel
- Edge drawing (click port → port to connect)
- Auto-layout (Dagre algorithm via npm package)
- Node selection, deletion, property editing
- JSON serialization/deserialization

**Phase 4.2: WorkflowEditor types + store integration**
- WorkflowDefinition, EditorNode, EditorEdge TypeScript types
- Integration with existing workflow.ts store

**Phase 4.3: WorkflowDetail.vue — Complete implementation**
- Workflow definition viewer (JSON view)
- Execution history list
- "Open Editor" button → navigate to editor

**Phase 4.4: WorkflowList.vue — Full CRUD**
- Search + pagination
- Create dialog (name, description, definition)
- Soft-delete with confirmation

**Phase 4.5: Editor routing + navigation**
- Route: `/workflows/:id/edit`
- Route: `/workflows/new`
- Toolbar: Save, Validate, Clear, Zoom controls

### Phase 5: Frontend — Auth UI + Polish
- [x] Add Login / Register pages with JWT token management
- [x] Store JWT in `localStorage`, attach to Axios headers
- [x] Add auth guard to router (redirect to login if unauthenticated)
- [x] Complete WorkflowDetail.vue: show definition, executions, edit button
- [x] Complete WorkflowList.vue: full CRUD, search, pagination
- [x] Add user profile dropdown in nav bar (already in App.vue)
- [x] **Deliverable:** Full frontend UX without dead UI elements
- **Status:** ✅ COMPLETE

### Phase 6: Infrastructure & Production
- [x] Create `Backend/Dockerfile` (multi-stage: build + production)
- [x] Create `Frontend/Dockerfile` with Nginx config
- [x] Write `nginx.conf` for SPA routing + API proxy
- [x] Update `docker-compose.yml` with health checks, restart policies, named volumes
- [x] Add `/health/` health check endpoint
- [x] Add `pytest` + `pytest-django` backend tests
- [x] Add Playwright E2E tests for critical flows
- [x] Write deployment guide in `DEPLOYMENT.md`
- [x] **Deliverable:** One-command production deployment
- **Status:** ✅ COMPLETE

---

## Architecture Decisions (ADRs)

| # | Decision | Rationale |
|---|----------|-----------|
| ADR-001 | JWT over Session auth | Stateless, scales horizontally, standard SPA pattern |
| ADR-002 | langgraph-checkpoint-django | Native Django ORM checkpointer, no extra DB needed |
| ADR-003 | SSE over WebSocket for streaming | Simpler, HTTP/2 friendly, sufficient for 1-way events |
| ADR-004 | Pinia over Vuex | Vue 3 native, better TypeScript support, lighter |

---

## Dependencies Between Phases

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
   │           │           │           │           │
   └───────────┴───────────┴───────────┴───────────┴── ✅ ALL COMPLETE (2026-04-20)
```

All phases are complete. The project is now at production-ready status.

---

## Phase 7: Visual Editor → Vue Flow (React Flow for Vue 3)

> **Status:** ✅ COMPLETE (2026-04-20)

### Decisions Made
| Decision | Choice |
|----------|--------|
| Library | `@vue-flow/core` v12 (Vue-native, not React Flow wrapper) |
| Scope | MVP — replaced SVG canvas only, kept existing toolbar/palette/inspector |
| Node types | Custom `BaseNode.vue` with typed handles per node type |
| Edge type | Custom `StyledEdge.vue` with smoothstep bezier + label + delete button |
| Layout | Automatic topological layout (Dagre-inspired, already in store) |
| Backward compat | Direct replacement — no fallback, removed pure SVG code |

### Implementation

**New files:**
- `src/utils/vueFlowBridge.ts` — bidirectional converter between EditorNode/EditorEdge ↔ Vue Flow Node/Edge
- `src/components/nodes/BaseNode.vue` — custom styled node with typed handles (chat/tool/condition/human_approval/parallel)
- `src/components/edges/StyledEdge.vue` — custom smoothstep edge with label, delete button, animated option

**Modified files:**
- `src/components/WorkflowEditor.vue` — replaced pure SVG canvas with `<VueFlow>` component, retained toolbar/palette/inspector
- Removed: all manual pan/zoom/mouse event handlers, SVG grid rendering, manual edge path calculations
- Kept: Element Plus toolbar buttons, node palette sidebar, property inspector panel, keyboard shortcuts, save/validation logic

**Key integration points:**
- Vue Flow `nodes` prop bound to `computed(() => editorNodesToVueFlow(store.nodes))` — store remains source of truth
- `onNodesChange` → delegates position updates to `store.moveNode()`
- `onConnect` → creates EditorEdge via `connectionToEditorEdge()`, validates duplicates in store
- `onNodeClick` / `onEdgeClick` → updates `store.selectedNodeId` / `store.selectedEdgeId`
- Auto-layout: calls `store.autoLayout()` + `fitView()` for smooth animation
- Drag-from-palette: HTML5 drag + `project()` to convert screen→flow coordinates

### ADR-005 Updated
| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| ADR-005 | Vue Flow for visual editor | Vue 3 native, not React wrapper; mature, active community; custom node/edge slots | ✅ Done (renamed from "React Flow") |

---

## Architecture Decisions (ADRs) — Expansion Phases

| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| ADR-001 | JWT over Session auth | Stateless, scales horizontally, standard SPA pattern | ✅ Done |
| ADR-002 | langgraph-checkpoint-django | Native Django ORM checkpointer, no extra DB needed | ✅ Done |
| ADR-003 | SSE over WebSocket for streaming | Simpler, HTTP/2 friendly, sufficient for 1-way events | ✅ Done |
| ADR-004 | Pinia over Vuex | Vue 3 native, better TypeScript support, lighter | ✅ Done |
| ADR-005 | Vue Flow for visual editor | Vue-native, not React wrapper; mature, active community; custom node/edge slots | ✅ Done |
| ADR-006 | Chroma over Qdrant/PGvector for RAG | Lightweight, embedded, Python-native, LangChain deep integration | Proposed |
| ADR-007 | Celery + Redis for async tasks | Django ecosystem standard, Redis already deployed | Proposed |
| ADR-008 | Langfuse over LangSmith | Self-hosted, data sovereignty, similar features | Proposed |
| ADR-009 | Guardrails AI + Microsoft Presidio | Guardrails for content filtering, Presidio for PII | Proposed |
| ADR-010 | LangChain MCP Adapters | Official LangChain MCP support, USB-like tool discovery | Proposed |

---

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| apps.py imported wrong module | `from ai_engine.graphs.basic_workflow import get_checkpointer` | Fixed: changed to `from ai_engine.workflow import get_workflow_graph` |
| Sync checkpointer with async nodes | `DjangoSaver` used with `astream()` (async nodes) | Fixed: replaced with `AsyncDjangoSaver` in `workflow.py` |
| AsyncDjangoSaver event loop crash | `get_running_loop()` fails when no loop active | Fixed: custom subclass injects loop via `get_event_loop()` |
| requirements.txt duplication | `langgraph`, `channels`, `simplejwt` repeated | Fixed: rewrote requirements.txt cleanly |
