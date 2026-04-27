# Findings & Decisions

## Research Findings
- (待补充) 技术栈/依赖/部署方式/运行入口将在扫描后填入。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 逐文件内容采用“关键摘要”而非全文粘贴 | “每个文件的作用和内容”可读性更重要，且避免导出文档过大/泄露敏感信息 |
| 忽略 `__pycache__/`、`.pyc` 等构建产物 | 这些不是源代码，且会造成噪音 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| | |

# Findings & Decisions — Flowly AI（项目现状与关键决策）

## 现状核对（以仓库当前代码为准）

### 当前系统能力摘要

**后端**（`Backend/ai_engine/`）：
- `workflow.py` — Phase 3 LangGraph graph with 7 nodes: router, approval_gate, parallel_executor, consolidate, tool_executor, general_assistant, finalize
- Send API parallel fan-out working
- LangGraph 检查点：当前环境检查显示 **未安装** `langgraph.checkpoint.django` 时会回退为内存（重启不持久化）
- Multi-model support: OpenAI, Claude, Ollama, VectorEngine
- 3 built-in tools: query_database, call_external_api, send_notification
- `WorkflowEventEmitter` via Django Channels → WebSocket
- 已包含：RAG（Document/Chroma）、Celery、媒体资源（LocalMediaAsset）、自动回复（AutoReply*）、平台密钥入库（PlatformAIProviderSecrets）

**前端**（`Frontend/src/`）：
- `WorkflowEditor.vue` — SVG-based visual editor (Phase 4)
- `workflowEditor.ts` — Pinia store with node/edge CRUD, layout, serialization
- `workflow.ts` — WebSocket-based execution streaming
- `auth.ts` — JWT with auto-refresh
- 工作流画布：已使用 Vue Flow（见 `WorkflowEditor.vue` 相关实现）

**基础设施**：
- MySQL 8.0, Redis 7, Django ASGI (Daphne), Vue + Nginx
- LangSmith tracing configured but not active (needs API key)
- Redis 同时用于 Channels 与 Celery（broker/backend）

---

## 技术决策（保留历史，但以当前实现为准）

| Decision | Rationale |
|----------|-----------|
| React Flow over custom SVG | Mature, Vue-compatible via adapter, active community, <200KB |
| Chroma over Qdrant/PGvector | Embedded mode, zero-dependency, LangChain deep integration |
| Celery over Dramatiq/RQ | Django ecosystem standard, Redis already deployed, Flower monitoring |
| Langfuse over LangSmith | Self-hosted, data sovereignty, similar features, avoids vendor lock-in |
| Guardrails AI + Presidio | Presidio best-in-class PII detection, Guardrails AI for content safety |
| LangChain MCP Adapters | Official LangChain support, plug-and-play MCP server discovery |
| OCR | 当前采用 `openocr-python`；已移除仓库内 `ocr_reference_bundle` 文件状态方案 |
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
