# Findings & Decisions — Flowly AI Feature Expansion

## Research Findings

### Current System Capabilities (Post Phase 1-6)

**Backend** (`Backend/ai_engine/`):
- `workflow.py` — Phase 3 LangGraph graph with 7 nodes: router, approval_gate, parallel_executor, consolidate, tool_executor, general_assistant, finalize
- Send API parallel fan-out working
- `DjangoSaver` checkpointing to MySQL
- Multi-model support: OpenAI, Claude, Ollama, VectorEngine
- 3 built-in tools: query_database, call_external_api, send_notification
- `WorkflowEventEmitter` via Django Channels → WebSocket
- No RAG, no Celery, no multimodal

**Frontend** (`Frontend/src/`):
- `WorkflowEditor.vue` — SVG-based visual editor (Phase 4)
- `workflowEditor.ts` — Pinia store with node/edge CRUD, layout, serialization
- `workflow.ts` — WebSocket-based execution streaming
- `auth.ts` — JWT with auto-refresh
- React Flow NOT yet integrated

**Infrastructure**:
- MySQL 8.0, Redis 7, Django ASGI (Daphne), Vue + Nginx
- LangSmith tracing configured but not active (needs API key)
- Redis available → can be Celery broker (no new infra)

---

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| React Flow over custom SVG | Mature, Vue-compatible via adapter, active community, <200KB |
| Chroma over Qdrant/PGvector | Embedded mode, zero-dependency, LangChain deep integration |
| Celery over Dramatiq/RQ | Django ecosystem standard, Redis already deployed, Flower monitoring |
| Langfuse over LangSmith | Self-hosted, data sovereignty, similar features, avoids vendor lock-in |
| Guardrails AI + Presidio | Presidio best-in-class PII detection, Guardrails AI for content safety |
| LangChain MCP Adapters | Official LangChain support, plug-and-play MCP server discovery |
| RapidOCR over Tesseract | Faster, better Chinese support, ONNX runtime |
| ConversationBufferMemory short-term | LangChain native, minimal overhead |
| Chroma for long-term memory | Unified vector store for RAG + memory |

---

## Architecture Considerations

### Key Extension Points

1. **workflow.py** — New nodes can be added as async functions, registered via `add_node()`
2. **get_tools()** — Extend with `@tool` decorated functions or MCP tools
3. **WorkflowState** — Can be extended with new TypedDict fields
4. **api.py** — Ninja routers modular, easy to add new endpoints
5. **models.py** — Django ORM, easy to add new models

### Integration Strategy

```
Phase 7 → React Flow
  └── Extends: Frontend rendering only, no backend change

Phase 8 → RAG
  └── New: Document model, vector_store.py, rag_retrieval_node
  └── Depends on: Phase 9 (for async document processing)

Phase 9 → Celery
  └── New: celery.py, tasks.py
  └── Depends on: None (standalone)
  └── Enables: Async RAG chunking, async document processing

Phase 13 → Security
  └── New: guardrails.py, pii_protection.py, security middleware
  └── Depends on: None

Phase 10 → Observability
  └── New: observability.py, cost_tracker.py, analytics API
  └── Depends on: Phase 9 (for task tracking)

Phase 11 → MCP
  └── New: mcp_client.py
  └── Depends on: None

Phase 12 → Multimodal
  └── New: multimodal.py, multimodal tools
  └── Depends on: Phase 9 (for async processing)

Phase 14 → LLMOps
  └── Infrastructure changes: replicas, Prometheus, Grafana
  └── Depends on: Phase 9

Phase 15 → Testing
  └── New: evaluation.py, judge.py
  └── Depends on: All phases

Phase 16 → Memory
  └── New: memory.py, long-term memory store
  └── Depends on: Phase 8 (vector store)
```

---

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| SVG editor lacks undo/redo, grouping, mini-map | Plan to replace with React Flow (Phase 7) |
| No async task support (workflows block HTTP) | Plan Celery integration (Phase 9) |
| No vector DB for RAG or long-term memory | Plan Chroma integration (Phase 8) |
| No content safety guardrails | Plan Guardrails AI + Presidio (Phase 13) |
| No cost tracking per LLM call | Plan cost_tracker.py (Phase 10) |
| No test evaluation framework | Plan LLM-as-Judge (Phase 15) |
