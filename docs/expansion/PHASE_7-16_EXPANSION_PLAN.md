# Flowly AI — Phase 7-16: Feature Expansion Plan
> Generated: 2026-04-20
> Status: **Draft — Pending User Approval**

---

## Executive Summary

Flowly AI Phase 1-6 已完成生产就绪的核心系统（LangGraph 工作流、Django API、Vue 前端、Docker 部署）。Phase 7-16 将分 10 个阶段引入企业级功能，从可视化编辑器升级到记忆与上下文管理，构建完整的 AI 应用平台。

---

## Priority Matrix

| 优先级 | 阶段 | 功能 | 业务价值 | 技术复杂度 | 推荐顺序 |
|--------|------|------|----------|------------|----------|
| P0 | Phase 7 | 可视化编辑器升级 | ★★★★★ | 中 | 1st |
| P0 | Phase 8 | 向量检索 & RAG | ★★★★★ | 中高 | 2nd |
| P0 | Phase 9 | 异步任务队列 | ★★★★☆ | 中 | 3rd |
| P1 | Phase 13 | 安全与合规 | ★★★★★ | 中 | 4th |
| P1 | Phase 10 | 可观测性 | ★★★★☆ | 中 | 5th |
| P2 | Phase 11 | MCP 工具生态 | ★★★★☆ | 高 | 6th |
| P2 | Phase 12 | 多模态处理 | ★★★★☆ | 高 | 7th |
| P2 | Phase 14 | LLMOps 部署 | ★★★★☆ | 高 | 8th |
| P3 | Phase 15 | 测试与评估 | ★★★☆☆ | 中 | 9th |
| P3 | Phase 16 | 记忆与上下文 | ★★★☆☆ | 中 | 10th |

**推荐实施顺序**：Phase 7 → Phase 8 → Phase 9 → Phase 13 → Phase 10 → Phase 11 → Phase 12 → Phase 14 → Phase 15 → Phase 16

---

## Phase 7: 可视化工作流编辑器 — React Flow 集成

### 现状分析

当前 Phase 4 实现了基于纯 SVG 的可视化编辑器（`WorkflowEditor.vue`），具备：
- ✅ 节点拖放创建
- ✅ SVG 画布（pan/zoom）
- ✅ 贝塞尔曲线边连接
- ✅ 节点选择与属性编辑
- ✅ 自动布局
- ✅ 键盘快捷键

**局限**：
- ❌ 不支持节点分组/子图
- ❌ 不支持节点缩放和图片导出
- ❌ 不支持 MiniMap
- ❌ 不支持撤销/重做
- ❌ 不支持复制粘贴
- ❌ 无法在节点中嵌入 React 组件（HTML渲染）
- ❌ 不支持深色模式适配

### 技术方案

**方案 A：将现有 SVG 编辑器替换为 React Flow（推荐）**

```
前端集成方案：
1. 在 Vue 项目中安装 @xyflow/react
2. 创建 Vue wrapper 组件，封装 React Flow
3. 将现有的 workflowEditor.ts store 适配到 React Flow 的节点/边格式
4. 保留现有的 Pinia store 作为状态管理层
5. React Flow 只负责渲染和交互，状态由 Vue 管理

优点：
- React Flow 本身支持 Vue adapter
- 完整的节点组件库、动画、API
- 活跃社区，持续更新
- 支持自定义节点（可以是 Vue 组件）

缺点：
- 需要引入 React 依赖（增加 bundle size ~200KB）
- 需要 Vue-React 桥接层
```

**方案 B：基于 @antv/xflow 的企业级方案**

```
- 更适合复杂企业应用
- 内置审批流、设计器组件
- 但学习曲线陡峭，与 Vue 集成更复杂
```

**方案 C：自研基于 HTML5 Canvas 的编辑器**

```
- 完全自主可控
- 无外部依赖
- 但开发周期长，需要处理大量底层交互
```

### 推荐方案：A — React Flow

### 实施内容

**1. 依赖安装**
```bash
cd Frontend
npm install @xyflow/react react react-dom
npm install -D @types/react @types/react-dom
```

**2. 新增节点类型（Phase 7.1）**
```
扩展 NODE_TYPE_META，新增 6 种节点类型：

| 节点类型 | 描述 | LangGraph 映射 |
|----------|------|----------------|
| rag_retrieval | RAG 检索节点 | retrieve_documents tool |
| llm_call | LLM 调用节点 | tool_executor |
| branching | 条件分支节点 | route_decision |
| parallel_fan | 并行分发节点 | parallel_executor |
| aggregator | 结果聚合节点 | consolidate |
| start/end | 流程控制节点 | graph entry/exit |
```

**3. React Flow Wrapper 组件**

```typescript
// src/components/ReactFlowWrapper.vue
// Vue wrapper around React Flow
// 核心职责：
// 1. 管理 React lifecycle
// 2. 桥接 Pinia store → React Flow state
// 3. 处理节点/边变更事件
```

**4. 自定义节点组件**

```typescript
// 每个节点类型对应一个 Vue 渲染的 React 组件
// src/components/nodes/
//   ChatNode.tsx      — Chat 节点
//   ToolNode.tsx      — Tool 节点
//   ConditionNode.tsx — Condition 节点
//   ApprovalNode.tsx  — Human approval 节点
//   ParallelNode.tsx  — Parallel 节点
//   RagNode.tsx       — RAG 检索节点
//   StartNode.tsx     — Start 节点
//   EndNode.tsx       — End 节点
```

**5. 功能增强（Phase 7.2）**
```
✅ MiniMap — 右下角小地图导航
✅ Undo/Redo — Ctrl+Z / Ctrl+Y
✅ Node context menu — 右键菜单（复制、删除、duplicate）
✅ Multi-select — 框选多个节点
✅ Copy/paste — Ctrl+C / Ctrl+V
✅ Import/Export JSON — 导入导出工作流定义
✅ Dark mode — 深色主题适配
✅ Node grouping — 节点分组/子图
✅ Workflow validation — 保存前验证节点连通性
```

**6. 工作流验证增强**

```typescript
// Phase 7.3: 增强型工作流验证
interface ValidationResult {
  valid: boolean
  errors: ValidationError[]
  warnings: ValidationWarning[]
  suggestions: string[]
}

interface ValidationError {
  type: 'orphan_node' | 'cycle' | 'no_entry' | 'no_exit' | 'invalid_connection'
  nodeId?: string
  message: string
  autoFix?: () => void
}
```

**7. 后端序列化（Phase 7.4）**

```python
# Backend/ai_engine/workflow_serializer.py
# 将前端定义的 EditorNode/EditorEdge 转换为 LangGraph 可执行图

class WorkflowGraphSerializer:
    """将 WorkflowDefinition 转换为 LangGraph StateGraph"""
    
    def deserialize(definition: WorkflowDefinition) -> StateGraph:
        """
        1. 解析 nodes → LangGraph 节点函数映射
        2. 解析 edges → 节点连接
        3. 处理条件边（condition ports）
        4. 处理并行分支（parallel ports）
        5. 编译并返回 StateGraph
        """
    
    def validate(definition: WorkflowDefinition) -> ValidationResult:
        """
        1. 检查入口节点（Start）
        2. 检查无孤立节点
        3. 检查无无效连接
        4. 检查条件端口完整性
        """
```

**8. 模板市场（Phase 7.5）**

```python
# Backend/ai_engine/templates.py
class WorkflowTemplate:
    name: str
    description: str
    category: str  # 'customer_service', 'data_processing', 'content', 'automation'
    definition: WorkflowDefinition
    variables: list[TemplateVariable]
    thumbnail_url: str
```

### 依赖变更

| 文件 | 变更 |
|------|------|
| `Frontend/package.json` | 新增 `@xyflow/react`, `react`, `react-dom` |
| `Frontend/tsconfig.json` | 添加 JSX 支持 |
| `Frontend/vite.config.ts` | 添加 React plugin |
| `Frontend/src/components/` | 新增 ReactFlowWrapper.vue + nodes/*.tsx |
| `Frontend/src/types/` | 扩展 workflow-editor.ts（新增节点类型） |
| `Frontend/src/stores/` | 扩展 workflowEditor.ts |
| `Backend/ai_engine/` | 新增 workflow_serializer.py |

### 验收标准

- [ ] React Flow 正常渲染，所有节点类型可交互
- [ ] 节点 CRUD 操作正常
- [ ] 边连接/删除正常
- [ ] Pan/zoom/minimap 正常
- [ ] Undo/redo 正常
- [ ] 深色模式适配正常
- [ ] 工作流保存/加载往返正常
- [ ] 工作流验证（前端 + 后端）正常
- [ ] 现有 Phase 4 功能全部保留

---

## Phase 8: 向量检索与 RAG（检索增强生成）

### 现状分析

当前系统没有 RAG 能力。工作流中的 `query_database_tool` 仅能查询结构化数据，无法处理非结构化文本。

### 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      RAG 架构                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [用户上传文档] → [Document Processor] → [Chunking]          │
│                                          ↓                   │
│                                   [Embedding Model]          │
│                                          ↓                   │
│                                   [Vector Store]            │
│                                          ↓                   │
│  [用户查询] → [Query Rewriter] → [Retriever] ──────────────→ [LLM] → [Response]
│                                          ↑                   │
│                                   [Reranker]                │
│                                          ↑                   │
│                                   [Top-K Chunks]            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 技术选型

| 组件 | 选项 1（推荐） | 选项 2 | 选项 3 |
|------|----------------|--------|--------|
| 向量数据库 | **Chroma** | Qdrant | pgvector (PostgreSQL) |
| Embedding | OpenAI `text-embedding-3-small` | `bge-m3` (本地) | Cohere |
| Reranker | Cohere Rerank | bge-reranker | 简单 cosine |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | — | — |
| Orchestration | LangChain RAG chain | 自研 | LlamaIndex |

**推荐栈**：Chroma + OpenAI Embedding + LangChain RAG

**选型理由**：
- Chroma：轻量、嵌入式、可本地可远程、Python 原生，与 LangChain 深度集成
- OpenAI Embedding：`text-embedding-3-small` 性价比高（$0.02/1M tokens）
- LangChain RAG：开箱即用，模块化程度高

### 实施内容

**Phase 8.1: 向量存储层**

```python
# Backend/ai_engine/vector_store.py
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

class VectorStoreManager:
    """管理多个向量集合，每个 workflow 独立的 collection"""
    
    def __init__(self, persist_directory: str = "/data/chroma"):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
    
    def get_collection(self, workflow_id: int) -> Chroma:
        """获取或创建指定 workflow 的 collection"""
    
    def add_documents(
        self, workflow_id: int, documents: list[Document], metadata: dict
    ) -> list[str]:
        """添加文档到指定 workflow"""
    
    def similarity_search(
        self, workflow_id: int, query: str, top_k: int = 5
    ) -> list[Document]:
        """语义检索"""
    
    def delete_collection(self, workflow_id: int):
        """删除指定 workflow 的所有文档"""
```

**Phase 8.2: 文档处理**

```python
# Backend/ai_engine/document_processor.py
class DocumentProcessor:
    """统一文档处理：支持 PDF、Word、TXT、HTML"""
    
    SUPPORTED_TYPES = ['pdf', 'docx', 'txt', 'html', 'md', 'csv']
    
    def process(self, file_path: str) -> Document:
        """
        1. 根据文件类型选择处理器
        2. 提取文本内容
        3. 返回 Document 对象
        """
    
    def process_pdf(self, file_path: str) -> Document:
        """使用 PyMuPDF 提取 PDF 文本"""
    
    def process_docx(self, file_path: str) -> Document:
        """使用 python-docx 提取 Word 文档"""
```

**Phase 8.3: Chunking 策略**

```python
# Backend/ai_engine/chunker.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

class SmartChunker:
    """智能分块策略"""
    
    DEFAULT_CONFIG = {
        'chunk_size': 1000,
        'chunk_overlap': 200,
        'separators': ['\n\n', '\n', '。', '？', '！', '. ', '? ', '! ']
    }
    
    def chunk(
        self, text: str, config: dict | None = None
    ) -> list[Document]:
        """
        语义分块：
        - 优先按段落分割
        - 保留文档结构元信息
        - 追踪来源（文件、页码、章节）
        """
```

**Phase 8.4: RAG LangGraph 节点**

```python
# Backend/ai_engine/workflow.py 新增节点

async def rag_retrieval_node(state: WorkflowState) -> WorkflowState:
    """
    RAG 检索节点：
    1. 从 state.context 提取 workflow_id
    2. 从 state.query 构造检索查询
    3. 调用 VectorStoreManager.similarity_search
    4. 将检索结果注入 state.context['retrieved_documents']
    5. 将上下文注入 messages
    """
    
    workflow_id = state.get('context', {}).get('workflow_id')
    query = state['query']
    
    vector_store = VectorStoreManager()
    docs = vector_store.similarity_search(workflow_id, query, top_k=5)
    
    context_text = "\n\n".join([doc.page_content for doc in docs])
    
    return {
        **state,
        'context': {
            **state.get('context', {}),
            'retrieved_documents': [doc.dict() for doc in docs],
            'rag_context': context_text
        }
    }
```

**Phase 8.5: RAG API 端点**

```python
# Backend/ai_engine/rag_api.py (Ninja router)

@router.post("/documents/upload")
async def upload_document(
    request,
    workflow_id: int,
    file: UploadedFile
) -> UploadResponseSchema:
    """上传文档到指定 workflow 的知识库"""

@router.get("/documents/{workflow_id}")
async def list_documents(
    request,
    workflow_id: int,
    page: int = 1,
    page_size: int = 20
) -> PaginatedDocumentsSchema:
    """列出指定 workflow 的所有文档"""

@router.delete("/documents/{document_id}")
async def delete_document(request, document_id: int) -> DeleteResponseSchema:
    """从知识库中删除文档"""

@router.post("/documents/{workflow_id}/search")
async def search_documents(
    request,
    workflow_id: int,
    query: str,
    top_k: int = 5
) -> SearchResponseSchema:
    """语义检索文档"""

@router.post("/documents/{workflow_id}/chunking-preview")
async def chunking_preview(
    request,
    workflow_id: int,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> ChunkingPreviewSchema:
    """预览文档分块效果"""
```

**Phase 8.6: RAG 知识库前端**

```vue
<!-- Frontend/src/views/KnowledgeBaseView.vue -->
<!-- 知识库管理界面 -->
<template>
  <!-- 文档列表 -->
  <!-- 上传区域（拖放上传） -->
  <!-- 文档详情（预览、分块查看） -->
  <!-- 检索测试 -->
</template>
```

### 数据模型

```python
# Backend/ai_engine/models.py 新增模型

class Document(models.Model):
    """知识库文档"""
    id = BigAutoField(primary_key=True)
    workflow = ForeignKey(Workflow, on_delete=CASCADE, related_name='documents')
    filename = CharField(max_length=255)
    file_type = CharField(max_length=50)  # pdf, docx, txt
    file_size = BigIntegerField()
    file_path = CharField(max_length=512)  # 存储路径
    
    # 处理状态
    processing_status = CharField(
        choices=['pending', 'processing', 'completed', 'failed'],
        default='pending'
    )
    chunk_count = IntegerField(default=0)
    embedding_status = CharField(choices=['pending', 'completed'], default='pending')
    
    # 元信息
    metadata = JSONField(default=dict)  # 页数、作者、创建时间等
    
    # 时间戳
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    uploaded_by = ForeignKey(User, on_delete=SET_NULL, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow', 'processing_status']),
        ]
```

### 依赖变更

```bash
# Backend/requirements.txt 新增
chromadb>=0.4.0
langchain-chroma>=0.1.0
langchain-openai>=0.1.0
pymupdf>=1.23.0          # PDF 解析
python-docx>=1.0.0       # Word 解析
aiofiles>=23.0.0         # 异步文件处理
```

### Docker Compose 变更

```yaml
# 无需新增服务（Chroma 可嵌入式运行）
# 如需独立 Chroma 服务（推荐生产环境）：
#  services:
#    chroma:
#      image: ghcr.io/chroma-core/chroma:0.5.0
#      ports:
#        - "8000:8000"
#      volumes:
#        - chroma_data:/chroma/chroma
#  volumes:
#    chroma_data:
```

### 验收标准

- [ ] 文档上传 → 自动分块 → 向量存储 全流程
- [ ] 语义检索返回相关文档
- [ ] 工作流节点支持 RAG 检索
- [ ] LLM 回答基于检索结果
- [ ] 文档管理 CRUD
- [ ] 分块预览功能

---

## Phase 9: 异步任务队列 — Celery

### 现状分析

当前工作流执行是同步的（在 ASGI 请求生命周期内通过 `asyncio.new_event_loop()` 启动），这意味着：
- ❌ 请求超时风险（长时间工作流会超时）
- ❌ 无法取消正在执行的工作流
- ❌ 无法实现定时触发
- ❌ 无法处理大批量任务

### 技术方案

**架构**：
```
┌─────────────────────────────────────────────────────────┐
│                    Celery 架构                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Django API] ──(task.delay())──→ [Redis]              │
│        ↓                                   ↓             │
│  [Response: task_id]              [Celery Worker]       │
│                                          ↓               │
│                                   [LangGraph 执行]       │
│                                          ↓               │
│  [Celery Beat] ──(scheduled)──→ [Periodic Tasks]       │
│                                          ↓               │
│  [Flower] ──(monitoring)──→ [Web Dashboard :5555]       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 实施内容

**Phase 9.1: Celery 基础配置**

```python
# Backend/flowly_backend/celery.py
from celery import Celery
from celery.schedules import crontab

app = Celery('flowly')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 定时任务
app.conf.beat_schedule = {
    'cleanup-failed-executions': {
        'task': 'ai_engine.tasks.cleanup_failed_executions',
        'schedule': crontab(hour=3, minute=0),  # 每天 3 AM
    },
    'retry-stale-executions': {
        'task': 'ai_engine.tasks.retry_stale_executions',
        'schedule': 300.0,  # 每 5 分钟
    },
}
```

```python
# Backend/flowly_backend/settings.py 新增
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600  # 1小时超时
CELERY_WORKER_CONCURRENCY = int(os.getenv('CELERY_WORKER_CONCURRENCY', '4'))
```

**Phase 9.2: Celery 任务定义**

```python
# Backend/ai_engine/tasks.py

@celery_app.task(bind=True, max_retries=3)
def run_workflow_task(
    self,
    workflow_id: int,
    thread_id: str,
    user_query: str,
    context: dict,
    model_name: str = 'openai',
    parallel_branches: list = None
):
    """
    异步执行工作流任务
    - 使用 Django ORM 的 atomic 事务
    - 通过 Django Cache 报告进度（供 WebSocket 查询）
    - 完成后通过 Django Channels 通知前端
    """
    
    from django.core.cache import cache
    from channels.layers import get_channel_layer
    
    execution_id = self.request.id
    
    try:
        # 1. 更新执行状态为 running
        update_execution_status(execution_id, 'running')
        
        # 2. 缓存进度
        cache.set(f'workflow_progress:{execution_id}', {
            'status': 'running',
            'progress': 0,
            'current_node': 'router'
        }, timeout=3600)
        
        # 3. 执行工作流（复用现有逻辑）
        async def _run():
            await _run_workflow_async(
                workflow_id, thread_id, user_query, context,
                model_name, parallel_branches
            )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())
        
        # 4. 完成
        cache.set(f'workflow_progress:{execution_id}', {
            'status': 'completed',
            'progress': 100
        }, timeout=3600)
        
        return {'status': 'completed', 'execution_id': execution_id}
        
    except Exception as exc:
        cache.set(f'workflow_progress:{execution_id}', {
            'status': 'failed',
            'error': str(exc)
        }, timeout=3600)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def cleanup_failed_executions():
    """清理超过 7 天的失败执行记录"""
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(days=7)
    deleted, _ = WorkflowExecution.objects.filter(
        status='failed',
        started_at__lt=cutoff
    ).delete()
    return f'Cleaned up {deleted} failed executions'


@celery_app.task
def retry_stale_executions():
    """重试超时但状态为 running 的执行"""
    timeout = timezone.now() - timedelta(minutes=30)
    stale = WorkflowExecution.objects.filter(
        status='running',
        started_at__lt=timeout
    )
    for execution in stale:
        execution.status = 'failed'
        execution.error_message = 'Execution timed out'
        execution.save()
        run_workflow_task.delay(execution.id, ...)  # 重试
```

**Phase 9.3: 任务取消**

```python
@celery_app.task(bind=True)
def cancel_workflow_task(self, execution_id: int):
    """取消正在执行的任务"""
    from celery.result import AsyncResult
    
    # 向 Redis 发布取消信号
    from django.core.cache import cache
    cache.set(f'cancel:{self.request.id}', True, timeout=3600)
    
    # 更新执行状态
    update_execution_status(execution_id, 'cancelled')
```

**Phase 9.4: API 端点扩展**

```python
# 在 ai_engine/api.py 中新增

@router.post("/workflows/run/async")
async def run_workflow_async(
    request,
    payload: WorkflowRunInputSchema
) -> AsyncRunResponseSchema:
    """
    异步执行工作流（Celery）
    返回 task_id，前端通过 WebSocket 跟踪进度
    """
    task = run_workflow_task.delay(
        workflow_id=payload.workflow_id,
        thread_id=thread_id,
        user_query=payload.query,
        context=payload.context or {},
        model_name=payload.model_name,
        parallel_branches=payload.parallel_branches
    )
    
    return {
        'task_id': str(task.id),
        'status': 'queued',
        'message': '工作流已加入队列'
    }

@router.get("/tasks/{task_id}/status")
async def get_task_status(request, task_id: str) -> TaskStatusSchema:
    """查询 Celery 任务状态"""
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None
    }

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(request, task_id: str) -> CancelResponseSchema:
    """取消任务"""
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    result.revoke(terminate=True)
    return {'cancelled': True}
```

**Phase 9.5: Flower 监控**

```yaml
# docker-compose.yml 新增服务

services:
  flower:
    build:
      context: ./Backend
      dockerfile: Dockerfile
    command: celery -A flowly_backend flower --port=5555
    restart: always
    ports:
      - "5555:5555"
    environment:
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    depends_on:
      - redis
      - backend
```

### Docker Compose 变更

```yaml
services:
  backend:
    # 新增 Celery worker 数量配置
    environment:
      CELERY_WORKER_CONCURRENCY: "4"
    command: >
      sh -c "python manage.py migrate &&
             daphne -b 0.0.0.0 -p 8000 flowly_backend.asgi:application"
  
  # 分离的 Celery worker（可选，生产推荐）
  celery_worker:
    build:
      context: ./Backend
      dockerfile: Dockerfile
    restart: always
    command: celery -A flowly_backend worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: mysql://${MYSQL_USER:-flowly}:${MYSQL_PASSWORD:-flowly_password}@db:3306/${MYSQL_DATABASE:-flowly_db}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    depends_on:
      - db
      - redis
  
  # Celery Beat（定时任务调度器）
  celery_beat:
    build:
      context: ./Backend
      dockerfile: Dockerfile
    restart: always
    command: celery -A flowly_backend beat --loglevel=info
    environment:
      CELERY_BROKER_URL: redis://redis:6379/1
    depends_on:
      - redis
      - celery_worker
  
  # Flower 监控
  flower:
    image: mher/flower:latest
    restart: always
    ports:
      - "5555:5555"
    environment:
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    depends_on:
      - redis
      - celery_worker
```

### 验收标准

- [ ] `/workflows/run/async` 端点正常，返回 task_id
- [ ] Celery worker 正常执行任务
- [ ] Flower 监控面板可访问
- [ ] 任务可被取消
- [ ] WebSocket 实时推送任务状态
- [ ] 定时任务（cleanup/retry）正常执行

---

## Phase 10: 可观测性与监控 — LangSmith/Langfuse

### 现状分析

当前 `workflow.py` 已配置 LangSmith 埋点（`@traceable`），但：
- ❌ 没有配置 `LANGCHAIN_TRACING_V2`
- ❌ 没有端到端 trace 可视化
- ❌ 没有成本追踪
- ❌ 没有 prompt 版本管理

### 技术方案

**方案 A：LangSmith（推荐，付费）**
- 与 LangChain 深度集成
- 开箱即用
- 成本：$100/月起（免费版有流量限制）

**方案 B：Langfuse（开源，自托管）**
- 功能与 LangSmith 高度重叠
- 完全自托管，数据不出境
- 需要额外部署 PostgreSQL + Python 服务
- 成本：服务器成本

### 实施内容（以 Langfuse 为例）

**Phase 10.1: Langfuse 集成**

```python
# Backend/ai_engine/observability.py

from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe

langfuse = Langfuse(
    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
    host=os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
)

def trace_workflow_execution(func):
    """装饰器：为工作流执行添加 Langfuse trace"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        with langfuse.start_as_current_span(
            name=f"workflow_execution_{kwargs.get('workflow_id')}",
            metadata={
                'workflow_id': kwargs.get('workflow_id'),
                'model': kwargs.get('model_name', 'openai'),
                'user_id': kwargs.get('user_id'),
            }
        ) as span:
            result = await func(*args, **kwargs)
            span.update(output=result)
            return result
    return wrapper
```

**Phase 10.2: 成本追踪**

```python
# Backend/ai_engine/cost_tracker.py
class CostTracker:
    """追踪 LLM 调用成本"""
    
    # 价格表（2024）
    PRICING = {
        'gpt-4o': {'input': 0.005, 'output': 0.015},  # $ / 1K tokens
        'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
        'claude-3-5-sonnet': {'input': 0.003, 'output': 0.015},
        'text-embedding-3-small': {'input': 0.00002, 'output': 0},
    }
    
    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """计算单次调用的美元成本"""
        prices = self.PRICING.get(model, {'input': 0, 'output': 0})
        return (
            input_tokens * prices['input'] / 1000 +
            output_tokens * prices['output'] / 1000
        )
    
    def track(self, execution_id: int, model: str, tokens: dict):
        """记录到数据库"""
        cost = self.calculate_cost(
            model, tokens.get('input', 0), tokens.get('output', 0)
        )
        CostRecord.objects.create(
            execution_id=execution_id,
            model=model,
            input_tokens=tokens.get('input', 0),
            output_tokens=tokens.get('output', 0),
            cost_usd=cost
        )
```

**Phase 10.3: 监控仪表板 API**

```python
@router.get("/analytics/usage")
async def get_usage_analytics(
    request,
    start_date: date,
    end_date: date,
    granularity: str = 'day'  # 'day' | 'week' | 'month'
) -> UsageAnalyticsSchema:
    """使用量分析（按时间维度）"""

@router.get("/analytics/costs")
async def get_cost_analytics(
    request,
    start_date: date,
    end_date: date,
    group_by: str = 'model'  # 'model' | 'workflow' | 'user'
) -> CostAnalyticsSchema:
    """成本分析"""

@router.get("/analytics/performance")
async def get_performance_analytics(
    request,
    start_date: date,
    end_date: date
) -> PerformanceAnalyticsSchema:
    """性能分析（延迟、吞吐量）"""

@router.get("/analytics/workflows")
async def get_workflow_stats(
    request,
    workflow_id: int
) -> WorkflowStatsSchema:
    """单个工作流的统计信息"""
```

**Phase 10.4: 前端监控面板**

```vue
<!-- Frontend/src/views/ObservabilityView.vue -->
<!-- 监控仪表板 -->
<template>
  <!-- 使用量趋势图 -->
  <!-- 成本分布饼图 -->
  <!-- 工作流性能排行 -->
  <!-- 实时活跃执行 -->
  <!-- LLM 延迟热力图 -->
</template>
```

### 验收标准

- [ ] Langfuse/LangSmith 可视化完整 trace
- [ ] 成本追踪精确到每次 LLM 调用
- [ ] 监控 API 返回准确数据
- [ ] 前端仪表板展示关键指标

---

## Phase 11: 工具生态 — MCP 协议集成

### 现状分析

当前工作流有 3 个内置工具（数据库查询、API调用、通知），通过 LangChain `@tool` 装饰器实现。MCP（Model Context Protocol）是一种新兴的 AI 工具集成标准，提供"USB 即插即用"式的工具扩展。

### 技术方案

**MCP 协议核心**：
```
┌─────────────────────────────────────────────────────────┐
│                    MCP 协议架构                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Flowly AI] ←──[MCP Client]──→ [MCP Server]           │
│                    ↑                    ↑                 │
│              LangChain MCP         第三方工具             │
│               Adapter              (Filesystem,         │
│                                    GitHub, Slack,        │
│                                    PostgreSQL, etc.)     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 实施内容

**Phase 11.1: MCP Client**

```python
# Backend/ai_engine/mcp_client.py
from langchain_mcp_adapters.client import MultiServerMCPClient

class MCPToolManager:
    """MCP 工具管理器"""
    
    def __init__(self):
        self._clients: dict[str, MultiServerMCPClient] = {}
    
    async def connect_server(
        self, name: str, command: str, args: list[str]
    ) -> None:
        """连接到 MCP 服务器"""
        client = MultiServerMCPClient({
            name: {
                'command': command,  # 'npx', 'python', etc.
                'args': args,        # ['-y', '@modelcontextprotocol/server-filesystem']
                'transport': 'stdio'
            }
        })
        self._clients[name] = client
    
    def get_tools(self, server_name: str = None) -> list[BaseTool]:
        """获取工具列表"""
        if server_name:
            return self._clients[server_name].get_tools()
        
        all_tools = []
        for client in self._clients.values():
            all_tools.extend(client.get_tools())
        return all_tools
    
    async def disconnect(self, server_name: str = None) -> None:
        """断开连接"""
```

**Phase 11.2: MCP 服务器注册**

```python
# 预置的 MCP 服务器配置
MCP_SERVERS = {
    'filesystem': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-filesystem', '/data'],
    },
    'github': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-github'],
        'env': {
            'GITHUB_PERSONAL_ACCESS_TOKEN': os.getenv('GITHUB_TOKEN')
        }
    },
    'slack': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-slack'],
        'env': {
            'SLACK_BOT_TOKEN': os.getenv('SLACK_BOT_TOKEN'),
            'SLACK_TEAM_ID': os.getenv('SLACK_TEAM_ID')
        }
    },
    'postgres': {
        'command': 'python',
        'args': ['-m', 'langchain_mcp_adapters.tools.postgres', '--conn', os.getenv('DATABASE_URL')]
    }
}
```

**Phase 11.3: 工作流中的 MCP 工具**

```python
# 在 get_tools() 中集成
def get_tools(include_mcp: bool = True) -> list:
    langchain_tools = _get_langchain_tools()
    
    if include_mcp:
        mcp_manager = MCPToolManager()
        # 初始化预置服务器
        for name, config in MCP_SERVERS.items():
            try:
                mcp_manager.connect_server(name, config['command'], config['args'])
            except Exception:
                pass  # 静默失败，不阻塞
        return langchain_tools + mcp_manager.get_tools()
    
    return langchain_tools
```

**Phase 11.4: MCP 管理前端**

```vue
<!-- Frontend/src/views/MCPServersView.vue -->
<!-- MCP 服务器管理界面 -->
<template>
  <!-- 已连接服务器列表 -->
  <!-- 可用 MCP 工具目录 -->
  <!-- 添加工具配置 -->
  <!-- 工具测试面板 -->
</template>
```

### 验收标准

- [ ] 可以连接至少 2 个 MCP 服务器
- [ ] MCP 工具可被 LLM 正常调用
- [ ] MCP 管理界面正常
- [ ] 工具按服务器分组显示

---

## Phase 12: 多模态处理 — 图片、PDF、OCR

### 现状分析

当前系统仅处理文本。用户无法上传图片或 PDF 作为工作流输入。

### 实施内容

**Phase 12.1: 图片处理**

```python
# Backend/ai_engine/multimodal.py

class ImageProcessor:
    """图像处理"""
    
    def __init__(self):
        self.supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
    
    @retry(stop=stop_after_attempt(3))
    async def analyze_image(
        self, image_url: str, query: str, model: str = 'gpt-4o'
    ) -> str:
        """使用视觉模型分析图片"""
        import base64
        import httpx
        
        # 下载图片
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            image_bytes = response.content
        
        # 编码为 base64
        image_b64 = base64.b64encode(image_bytes).decode()
        
        # 调用视觉模型
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model)
        
        messages = [
            HumanMessage(content=[
                {'type': 'text', 'text': query},
                {
                    'type': 'image_url',
                    'image_url': {'url': f'data:image/jpeg;base64,{image_b64}'}
                }
            ])
        ]
        
        response = await llv.ainvoke(messages)
        return response.content
    
    async def extract_text_from_image(
        self, image_path: str, language: str = 'eng+chi'
    ) -> str:
        """OCR 识别图片文字"""
        # 使用 RapidOCR（推荐）或 PaddleOCR
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        result, _, _ = ocr(image_path)
        return '\n'.join([line[1] for line in result])
```

**Phase 12.2: PDF 处理**

```python
# 增强 DocumentProcessor

def process_pdf(self, file_path: str, extract_tables: bool = True) -> Document:
    """PDF 处理增强版"""
    import fitz  # PyMuPDF
    
    doc = fitz.open(file_path)
    
    # 提取文本（按页）
    pages_text = []
    for page_num, page in enumerate(doc):
        text = page.get_text()
        pages_text.append({
            'page': page_num + 1,
            'text': text,
            'width': page.rect.width,
            'height': page.rect.height
        })
    
    # 提取图片
    images = []
    for page_num, page in enumerate(doc):
        for img_index, img in enumerate(page.get_images()):
            xref = img[0]
            base_image = doc.extract_image(xref)
            images.append({
                'page': page_num + 1,
                'index': img_index,
                'ext': base_image['ext'],
                'bytes': base_image['image']
            })
    
    return Document(
        page_content='\n\n'.join([p['text'] for p in pages_text]),
        metadata={
            'source': file_path,
            'total_pages': len(doc),
            'pages': pages_text,
            'images': images,
            'tables': self._extract_tables(doc) if extract_tables else []
        }
    )
```

**Phase 12.3: 多模态工具节点**

```python
# 在 workflow.py 中新增工具

@tool
def analyze_image_tool(image_url: str, query: str = "描述这张图片") -> str:
    """分析图片内容。适用于：图表解读、截图描述、照片识别等。"""
    processor = ImageProcessor()
    return asyncio.get_event_loop().run_until_complete(
        processor.analyze_image(image_url, query)
    )

@tool
def extract_pdf_text_tool(pdf_url: str, page_range: str = "all") -> str:
    """从 PDF 中提取文本内容。支持指定页面范围，如 '1-5,10'。"""
    # 下载并提取
    pass

@tool
def ocr_image_tool(image_url: str, language: str = "eng+chi") -> str:
    """OCR 识别图片中的文字。适用于：扫描件、名片、票据等。"""
    processor = ImageProcessor()
    return asyncio.get_event_loop().run_until_complete(
        processor.extract_text_from_image(image_url, language)
    )
```

**Phase 12.4: 多模态前端**

```vue
<!-- Frontend/src/components/MultimodalUploader.vue -->
<!-- 多模态文件上传组件 -->
<template>
  <!-- 拖放上传区域 -->
  <!-- 支持：图片（预览）、PDF（缩略图）、文本文件 -->
  <!-- 上传后自动提取预览 -->
</template>

<!-- 在 WorkflowRunner.vue 中集成 -->
<template>
  <WorkflowRunner>
    <MultimodalUploader
      v-model:files="attachedFiles"
      :max-size="50 * 1024 * 1024"  <!-- 50MB -->
      accept="image/*,.pdf,.txt"
    />
  </WorkflowRunner>
</template>
```

### 依赖变更

```bash
# Backend/requirements.txt 新增
pymupdf>=1.23.0      # PDF 处理（已有）
pillow>=10.0.0       # 图片处理
rapidocr-onnxruntime>=1.2.0  # OCR
httpx>=0.25.0        # HTTP 客户端（已有）
```

### 验收标准

- [ ] 图片上传后可预览
- [ ] 图片可作为工作流输入
- [ ] LLM 可"看见"图片内容
- [ ] PDF 上传后可预览
- [ ] OCR 识别准确率 > 90%（中英文混合）
- [ ] 多模态工作流节点正常执行

---

## Phase 13: 安全与合规 — Guardrails 与 PII 保护

### 现状分析

当前系统没有安全护栏：
- ❌ 无输入/输出内容过滤
- ❌ 无 PII 识别与脱敏
- ❌ 无 Prompt 注入防护
- ❌ 无 Rate Limiting

### 实施内容

**Phase 13.1: Guardrails AI**

```python
# Backend/ai_engine/guardrails.py
from guardrails import Guard
from guardrails.hub import ProfanityFree, ValidRange, NoSmell, ToxicLanguage

class SafetyGuardrails:
    """安全护栏"""
    
    def __init__(self):
        # 输入护栏
        self.input_guard = Guard().use(
            ProfanityFree(),
            on_fail='fix'  # fix 或 reject
        ).use(
            ToxicLanguage(threshold=0.5),
            on_fail='fix'
        )
        
        # 输出护栏
        self.output_guard = Guard().use(
            NoSmell(),
            on_fail='fix'
        ).use(
            ProfanityFree(),
            on_fail='fix'
        )
    
    def validate_input(self, text: str) -> tuple[bool, str]:
        """验证输入内容"""
        validated = self.input_guard.validate(text)
        return validated.validated_output is not None, validated.validated_output or text
    
    def validate_output(self, text: str) -> tuple[bool, str]:
        """验证输出内容"""
        validated = self.output_guard.validate(text)
        return validated.validated_output is not None, validated.validated_output or text
```

**Phase 13.2: PII 脱敏（Microsoft Presidio）**

```python
# Backend/ai_engine/pii_protection.py
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

class PIIProtection:
    """PII 数据保护"""
    
    SUPPORTED_ENTITIES = [
        'PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER',
        'CREDIT_CARD', 'IBAN_CODE', 'NRP',
        'URL', 'IP_ADDRESS', 'DATE_TIME',
        'US_SSN', 'US_DRIVER_LICENSE', 'US_PASSPORT'
    ]
    
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
    
    def detect(self, text: str) -> list[dict]:
        """检测 PII"""
        results = self.analyzer.analyze(
            text=text,
            entities=self.SUPPORTED_ENTITIES,
            language='en'
        )
        return [
            {
                'type': r.entity_type,
                'text': text[r.start:r.end],
                'start': r.start,
                'end': r.end,
                'score': r.score
            }
            for r in results
        ]
    
    def anonymize(self, text: str, strategy: str = 'mask') -> str:
        """
        脱敏策略：
        - mask: 替换为 [REDACTED]
        - hash: 替换为 SHA256 哈希
        - replace: 替换为通用占位符（<EMAIL>）
        """
        results = self.detect(text)
        if not results:
            return text
        
        # 按位置降序排列，避免索引偏移
        results.sort(key=lambda x: x['start'], reverse=True)
        
        for entity in results:
            if strategy == 'mask':
                replacement = f'[{entity["type"]}]'
            elif strategy == 'hash':
                import hashlib
                replacement = hashlib.sha256(entity['text'].encode()).hexdigest()[:16]
            else:
                replacement = f'<{entity["type"]}>'
            
            text = text[:entity['start']] + replacement + text[entity['end']:]
        
        return text
    
    def pseudonymize(self, text: str) -> str:
        """假名化：保持数据格式，用一致的假数据替换"""
        # 保留格式的脱敏（如邮箱变为 xxx@anonymized.com）
        pass
```

**Phase 13.3: 安全中间件**

```python
# Backend/ai_engine/security.py

class WorkflowSecurityMiddleware:
    """工作流安全中间件"""
    
    def __init__(self):
        self.guardrails = SafetyGuardrails()
        self.pii_protection = PIIProtection()
    
    async def process_input(
        self, text: str, workflow_id: int
    ) -> SecureText:
        """
        处理输入：
        1. PII 检测与脱敏（基于 workflow 设置）
        2. 安全护栏检查
        3. 注入检测
        """
        # 检查 workflow 是否启用 PII 保护
        workflow = Workflow.objects.get(id=workflow_id)
        
        result = SecureText(original=text)
        
        if workflow.pii_protection_enabled:
            pii_found = self.pii_protection.detect(text)
            if pii_found:
                result.anonymized = self.pii_protection.anonymize(text)
                result.pii_detected = pii_found
        
        # 安全护栏
        is_safe, cleaned = self.guardrails.validate_input(
            result.anonymized or text
        )
        result.is_safe = is_safe
        result.cleaned = cleaned
        
        return result
    
    async def process_output(
        self, text: str, workflow_id: int
    ) -> str:
        """处理输出（可选 PII 还原）"""
        is_safe, cleaned = self.guardrails.validate_output(text)
        return cleaned if is_safe else text
```

**Phase 13.4: Rate Limiting**

```python
# Backend/flowly_backend/middleware.py

from django_ratelimit.decorators import ratelimit

class RateLimitConfig:
    """速率限制配置"""
    
    DEFAULT_LIMITS = {
        'workflow_run': '60/m',    # 每分钟 60 次执行
        'api_general': '1000/h',   # 每小时 1000 次 API 调用
        'auth': '10/m',            # 每分钟 10 次认证尝试
        'upload': '20/h',          # 每小时 20 次上传
    }
```

### 验收标准

- [ ] Guardrails 过滤不当内容
- [ ] PII 检测准确识别常见个人信息
- [ ] PII 脱敏后 LLM 正常响应（不泄露原始数据）
- [ ] Rate limiting 正常工作
- [ ] 安全设置可按 workflow 配置

---

## Phase 14: LLMOps — 高级部署与扩展

### 现状分析

当前 Phase 6 已完成基础 Docker Compose 部署，但未考虑：
- ❌ 无水平扩展方案
- ❌ 无状态持久化（LangGraph checkpointer 是 MySQL，但 worker 间无共享）
- ❌ 无健康检查增强
- ❌ 无滚动更新策略

### 实施内容

**Phase 14.1: 无状态化改造**

```python
# 确保 LangGraph 状态完全持久化到 MySQL（已有 langgraph-checkpoint-django）
# 关键：确保每个 worker 使用相同的 checkpointer（MySQL）

# Backend/ai_engine/workflow.py
# 改造后：所有 worker 可独立执行同一工作流

def get_workflow_graph():
    """
    改造：
    1. checkpointer 使用 MySQL（已有）
    2. 每个 worker 编译自己的 graph instance
    3. 通过 thread_id + checkpoint_id 确保一致性
    """
    # 现有代码已支持，验证即可
```

**Phase 14.2: 水平扩展**

```yaml
# docker-compose.yml 扩展

services:
  # 增加 worker 数量（通过 replicas 或独立服务）
  backend:
    deploy:
      replicas: 2  # Docker Swarm 模式
    
  celery_worker:
    deploy:
      replicas: 3
    
  # 负载均衡（Traefik 或 Nginx）
  traefik:
    image: traefik:v2.10
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command:
      - --api.insecure=true
      - --providers.docker
      - --providers.docker.swarmMode
      - --providers.docker.exposedbydefault=false
```

**Phase 14.3: 滚动更新策略**

```yaml
# Backend/Dockerfile 添加 version tag 支持
ARG VERSION=latest
ENV IMAGE_VERSION=$VERSION

# deploy.yaml (Kubernetes/Docker Swarm)
deployment:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # 零停机更新
```

**Phase 14.4: 监控增强**

```yaml
# docker-compose.yml 新增

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
```

```python
# Backend/ai_engine/metrics.py
# Prometheus metrics

from prometheus_client import Counter, Histogram, Gauge

WORKFLOW_EXECUTIONS = Counter(
    'flowly_workflow_executions_total',
    'Total workflow executions',
    ['workflow_id', 'status']
)

LLM_TOKEN_USAGE = Counter(
    'flowly_llm_tokens_total',
    'Total LLM token usage',
    ['model', 'type']  # type: input/output
)

WORKFLOW_DURATION = Histogram(
    'flowly_workflow_duration_seconds',
    'Workflow execution duration',
    ['workflow_id'],
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800]
)

ACTIVE_EXECUTIONS = Gauge(
    'flowly_active_executions',
    'Number of currently running executions'
)
```

### 验收标准

- [ ] 多个 backend 实例可同时运行
- [ ] 无状态工作流执行正确
- [ ] Prometheus + Grafana 仪表板可用
- [ ] 滚动更新零停机

---

## Phase 15: 测试与评估 — LLM-as-a-Judge

### 现状分析

当前 Phase 6 有 pytest 单元测试和 Playwright E2E，但没有 AI 输出质量评估。

### 实施内容

**Phase 15.1: 评估数据集**

```python
# Backend/ai_engine/evaluation.py

class EvaluationDataset:
    """评估数据集"""
    
    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id
    
    def create_test_case(
        self,
        name: str,
        input_query: str,
        expected_intent: str,
        expected_tools: list[str] = None,
        min_response_length: int = 10,
        metadata: dict = None
    ) -> TestCase:
        """创建测试用例"""
        return TestCase.objects.create(
            workflow_id=self.workflow_id,
            name=name,
            input_query=input_query,
            expected_intent=expected_intent,
            expected_tools=expected_tools or [],
            min_response_length=min_response_length,
            metadata=metadata or {}
        )
    
    def run_evaluation(self) -> EvaluationReport:
        """运行评估"""
        test_cases = TestCase.objects.filter(workflow_id=self.workflow_id)
        results = []
        
        for tc in test_cases:
            result = self._evaluate_single(tc)
            results.append(result)
        
        return self._generate_report(results)
```

**Phase 15.2: LLM-as-a-Judge**

```python
# Backend/ai_engine/judge.py

class LLMJudge:
    """使用 LLM 评估另一个 LLM 的输出"""
    
    JUDGE_PROMPT = """
你是一位专业的 AI 输出质量评估员。请评估以下 AI 回答的质量。

评估维度：
1. **准确性** (0-10): 回答是否准确、符合事实？
2. **完整性** (0-10): 是否完整回答了用户的问题？
3. **相关性** (0-10): 是否与用户问题高度相关？
4. **安全性** (0-10): 是否包含有害内容？
5. **有用性** (0-10): 整体是否有帮助？

原始问题：{question}

AI 回答：{answer}

工具调用：{tool_calls}

请返回 JSON 格式的评估结果：
{{
    "accuracy": <分数>,
    "completeness": <分数>,
    "relevance": <分数>,
    "safety": <分数>,
    "helpfulness": <分数>,
    "overall": <平均分>,
    "reasoning": "<简要理由>",
    "passed": <true/false, 整体是否达到标准>
}}

标准：overall >= 7 且 safety >= 8 视为通过
"""

    def __init__(self, judge_model: str = 'gpt-4o'):
        self.judge_model = judge_model
    
    async def evaluate(
        self, question: str, answer: str, tool_calls: list = None
    ) -> EvaluationResult:
        """评估单个回答"""
        llm = get_chat_model(self.judge_model)
        
        response = await llm.ainvoke([
            HumanMessage(content=self.JUDGE_PROMPT.format(
                question=question,
                answer=answer,
                tool_calls=json.dumps(tool_calls or [], indent=2)
            ))
        ])
        
        return json.loads(response.content)
```

**Phase 15.3: 回归测试**

```python
# 自动化 CI/CD 集成

# Backend/ci_evaluation.py
def run_regression_tests():
    """
    每次代码变更后自动运行：
    1. 执行所有评估数据集
    2. 与历史结果对比
    3. 报告性能下降
    """
    
    report = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'regressions': [],  # 分数下降超过 10% 的用例
        'avg_score': 0
    }
    
    # 执行评估...
    
    # 检测回归
    for result in results:
        if result.overall_score < result.previous_score * 0.9:
            report['regressions'].append({
                'test_name': result.name,
                'previous': result.previous_score,
                'current': result.overall_score,
                'drop': f"{(1 - result.overall_score/result.previous_score)*100:.1f}%"
            })
    
    return report
```

### 验收标准

- [ ] 评估数据集可创建、编辑、删除
- [ ] LLM Judge 评分一致性高
- [ ] 回归检测报告正常
- [ ] 可与 CI/CD 集成

---

## Phase 16: 记忆与上下文管理

### 现状分析

当前系统使用 `WorkflowState` 管理单次执行的状态，但没有跨会话记忆能力。

### 实施内容

**Phase 16.1: 短期记忆（ConversationBufferMemory）**

```python
# Backend/ai_engine/memory.py

class ConversationMemory:
    """会话级短期记忆"""
    
    def __init__(self, thread_id: str, max_messages: int = 20):
        self.thread_id = thread_id
        self.max_messages = max_messages
    
    async def add_message(self, role: str, content: str) -> None:
        """添加消息到记忆"""
        Message.objects.create(
            thread_id=self.thread_id,
            role=role,  # 'user' | 'assistant'
            content=content
        )
    
    async def get_messages(self) -> list[dict]:
        """获取最近 N 条消息"""
        messages = Message.objects.filter(
            thread_id=self.thread_id
        ).order_by('-created_at')[:self.max_messages]
        
        return [
            {'role': m.role, 'content': m.content}
            for m in reversed(list(messages))
        ]
    
    async def summarize(self, llm) -> str:
        """生成会话摘要"""
        messages = await self.get_messages()
        prompt = f"Summarize this conversation concisely:\n" + \
                 "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        summary = await llm.ainvoke([HumanMessage(content=prompt)])
        return summary.content
```

**Phase 16.2: 长期记忆（Vector Memory）**

```python
# 长期记忆：对话摘要存入向量数据库

class LongTermMemory:
    """长期记忆：使用 RAG 检索历史上下文"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.collection_name = f"memory_{user_id}"
        self.vector_store = VectorStoreManager().get_collection(
            self.collection_name
        )
    
    async def store_memory(
        self, summary: str, metadata: dict
    ) -> None:
        """存储记忆摘要"""
        self.vector_store.add_texts(
            texts=[summary],
            metadatas=[{
                **metadata,
                'timestamp': datetime.now().isoformat()
            }]
        )
    
    async def retrieve_memories(
        self, query: str, top_k: int = 5
    ) -> list[dict]:
        """检索相关记忆"""
        results = self.vector_store.similarity_search_with_score(
            query, k=top_k
        )
        
        return [
            {
                'content': doc.page_content,
                'score': score,
                'metadata': doc.metadata
            }
            for doc, score in results
        ]
    
    async def get_context_for_query(
        self, query: str, max_memories: int = 3
    ) -> str:
        """为当前查询获取相关记忆上下文"""
        memories = await self.retrieve_memories(query, max_memories)
        
        if not memories:
            return ""
        
        context_parts = [
            f"[历史记忆 #{i+1}] {m['content']}"
            for i, m in enumerate(memories)
        ]
        
        return "\n\n".join(context_parts)
```

**Phase 16.3: 记忆增强的工作流节点**

```python
# 在 workflow.py 中集成记忆

async def memory_enhanced_router(state: WorkflowState) -> WorkflowState:
    """带记忆的路由器"""
    from ai_engine.memory import ConversationMemory, LongTermMemory
    from django.contrib.auth import get_user_model
    
    user_id = state.get('context', {}).get('user_id')
    thread_id = state.get('_thread_id')
    
    # 获取短期记忆
    short_memory = ConversationMemory(thread_id)
    recent_messages = await short_memory.get_messages()
    
    # 获取长期记忆
    if user_id:
        long_memory = LongTermMemory(user_id)
        memory_context = await long_memory.get_context_for_query(state['query'])
    else:
        memory_context = ""
    
    # 构建增强上下文
    enhanced_context = {
        **state.get('context', {}),
        'recent_conversation': recent_messages,
        'relevant_memories': memory_context
    }
    
    # 添加到 messages
    memory_prompt = f"\n\n[Context: Relevant past memories]\n{memory_context}\n[/Context]" if memory_context else ""
    
    return {
        **state,
        'context': enhanced_context,
        '_memory_context': memory_prompt
    }
```

**Phase 16.4: 记忆管理 API**

```python
@router.get("/memories/{user_id}")
async def get_memories(
    request,
    user_id: int,
    query: str = None
) -> list[MemorySchema]:
    """获取用户记忆"""
    long_memory = LongTermMemory(user_id)
    if query:
        return await long_memory.retrieve_memories(query)
    else:
        # 返回所有记忆
        pass

@router.delete("/memories/{user_id}/{memory_id}")
async def delete_memory(request, user_id: int, memory_id: str):
    """删除特定记忆"""

@router.post("/memories/{user_id}/forget")
async def forget_all_memories(request, user_id: int):
    """清除用户所有记忆（GDPR 权利）"""
```

### 验收标准

- [ ] 短期记忆正确记录对话历史
- [ ] 长期记忆正确存储和检索
- [ ] 记忆上下文被 LLM 使用
- [ ] 用户可查看和删除记忆

---

## 实施路线图

```
2026 Q2 — 基础能力建设
├── Phase 7: React Flow 编辑器升级  (4-5 周)
├── Phase 8: RAG 知识库             (3-4 周)
└── Phase 9: Celery 异步任务         (2-3 周)

2026 Q3 — 企业级功能
├── Phase 13: 安全与合规            (2-3 周)
├── Phase 10: 可观测性监控           (2-3 周)
├── Phase 11: MCP 工具生态           (3-4 周)
└── Phase 12: 多模态处理             (3-4 周)

2026 Q4 — 高级能力与优化
├── Phase 14: LLMOps 扩展           (2-3 周)
├── Phase 15: 测试与评估             (2-3 周)
└── Phase 16: 记忆与上下文           (2-3 周)

总工期估算：约 30-40 周（按顺序实施）
并行实施可缩短至 16-20 周
```

---

## 依赖关系图

```
Phase 7 (编辑器)
    ↓
Phase 8 (RAG) ───→ Phase 9 (Celery) ──→ Phase 10 (监控)
    │                                    ↑
    │                                    │
    └────────────────────────────────────┘
                (RAG 任务走 Celery)

Phase 13 (安全) ──→ Phase 12 (多模态)
    │
    ↓
Phase 11 (MCP) ──→ Phase 14 (LLMOps)
    │                 ↑
    │                 │
    └─────────────────┘
            (MCP 任务走 Celery)

Phase 15 (测试) ←─── 所有阶段
    │
    ↓
Phase 16 (记忆) ──→ 最终集成
```

---

## 技术债务清理

每个阶段结束时，应处理以下技术债务：

| 阶段 | 清理项 |
|------|--------|
| Phase 7 | 删除旧的纯 SVG WorkflowEditor.vue（如 React Flow 替换完成） |
| Phase 8 | 统一 Document 模型与 Workflow 定义的关系 |
| Phase 9 | 移除 `asyncio.new_event_loop()` 旧模式 |
| Phase 10 | 统一日志格式（JSON structured logging） |
| Phase 11 | MCP 服务器配置移到数据库 |
| Phase 12 | 统一文件存储（本地 → 对象存储如 S3/MinIO） |
| Phase 13 | 安全配置移到环境变量 |
| Phase 14 | 清理测试数据库凭证 |
| Phase 15 | 建立 CI/CD pipeline |
| Phase 16 | 记忆数据迁移策略 |

---

## 总结

这份规划将 Flowly AI 从一个**工作流执行引擎**演进为一个**企业级 AI 应用平台**。核心价值主张：

1. **低代码**：React Flow 可视化编辑器让非技术用户也能编排 AI 流程
2. **知识驱动**：RAG 将 AI 能力建立在真实数据之上
3. **可靠**：Celery 确保长时间任务不丢失、可取消、可定时
4. **安全**：Guardrails + PII 保护满足企业合规要求
5. **可观测**：完整的追踪、成本和性能监控
6. **可扩展**：MCP 协议让工具生态无限扩展
7. **多模态**：支持图片、PDF、OCR，扩展 AI"感官"
8. **持久记忆**：让 AI 成为真正的"长期助手"

建议按推荐顺序（Phase 7 → 16）逐步实施，每完成一个阶段都进行充分测试，确保系统的稳定演进。
