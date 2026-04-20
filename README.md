# Flowly AI

> 基于 Django + LangGraph + Vue 3 的 AI 工作流引擎，支持可视化编排、实时流式响应、向量检索与异步任务处理。

---

## 项目概览

Flowly AI 是一个企业级 AI 工作流平台，核心能力包括：

- **可视化工作流编辑器** — 基于 Vue Flow 的拖拽式节点编排
- **LangGraph 工作流引擎** — 支持并行节点、条件路由、人机交互、多模型切换
- **实时流式响应** — Django Channels + WebSocket 驱动的 SSE/流式输出
- **RAG 向量检索** — 支持 PDF/Word 文档解析与语义搜索
- **异步任务队列** — Celery + Redis 实现后台任务调度
- **可观测性面板** — 执行追踪、成本分析、性能监控

---

## 目录结构

```
Flowly-AI/
│
├── Backend/                        # Django 后端
│   ├── ai_engine/                 # AI 引擎应用
│   │   ├── workflow.py            # LangGraph 工作流核心（~1600行）
│   │   ├── workflows.py           # 工作流 CRUD API
│   │   ├── executions.py           # 执行历史与统计
│   │   ├── api.py                 # Django Ninja REST API（~800行）
│   │   ├── rag_api.py             # RAG / 向量检索 API
│   │   ├── rag_models.py          # Document / Chunk 数据模型
│   │   ├── task_api.py            # Celery 任务管理 API
│   │   ├── analytics_api.py       # 可观测性分析 API
│   │   ├── analytics_models.py    # 执行记录/成本追踪模型
│   │   ├── vector_store.py        # ChromaDB 向量存储封装
│   │   ├── document_processor.py   # PDF/Word 文档处理
│   │   ├── chunker.py             # 文档分块策略
│   │   ├── tasks.py               # Celery 异步任务定义
│   │   ├── cost_tracker.py        # LLM 成本追踪
│   │   ├── auth.py               # JWT 认证工具
│   │   ├── consumers.py           # Django Channels WebSocket 消费者
│   │   ├── graphs/                # LangGraph 子图定义
│   │   ├── migrations/            # 数据库迁移
│   │   └── models.py              # 数据模型
│   ├── accounts/                  # 用户认证应用
│   ├── checkpoint/                # LangGraph 状态持久化（DjangoSaver）
│   ├── flowly_backend/             # Django 项目配置
│   │   ├── settings.py            # 核心配置
│   │   ├── urls.py                # 根路由
│   │   ├── asgi.py               # ASGI 应用（支持 WebSocket）
│   │   └── wsgi.py               # WSGI 应用
│   ├── manage.py                  # Django 管理脚本
│   ├── requirements.txt           # Python 依赖
│   ├── Dockerfile                 # 后端容器镜像
│   ├── .env.example               # 环境变量模板
│   └── conftest.py               # Pytest 配置
│
├── Frontend/                      # Vue 3 前端
│   ├── src/
│   │   ├── views/                 # 页面视图
│   │   │   ├── Home.vue           # 首页仪表盘
│   │   │   ├── Chat.vue           # AI 聊天界面
│   │   │   ├── DashboardView.vue  # 工作流列表与概览
│   │   │   ├── WorkflowDetail.vue # 工作流详情与执行记录
│   │   │   ├── WorkflowEditorView.vue  # 可视化编辑器入口
│   │   │   ├── WorkflowList.vue   # 工作流管理列表
│   │   │   ├── WorkflowRunView.vue    # 工作流执行视图
│   │   │   ├── KnowledgeBaseView.vue  # 知识库管理（RAG）
│   │   │   ├── ObservabilityView.vue  # 可观测性面板
│   │   │   ├── Settings.vue       # 系统设置
│   │   │   ├── AuthPage.vue       # 登录/注册页面
│   │   │   └── About.vue          # 关于页面
│   │   ├── components/
│   │   │   ├── WorkflowEditor.vue # 可视化工作流编辑器（~870行）
│   │   │   ├── WorkflowMonitor.vue # 执行状态监控（~430行）
│   │   │   ├── WorkflowRunner.vue  # 工作流运行器
│   │   │   ├── BgCubeCanvas.vue   # 3D 背景画布
│   │   │   └── nodes/edges/        # 自定义节点与边组件
│   │   ├── stores/                # Pinia 状态管理
│   │   ├── router/                # Vue Router 配置
│   │   ├── types/                 # TypeScript 类型定义
│   │   ├── utils/                 # 工具函数
│   │   ├── styles/                # 全局样式
│   │   ├── assets/                # 静态资源
│   │   ├── App.vue               # 根组件
│   │   └── main.ts               # 应用入口
│   ├── package.json               # Node 依赖
│   ├── vite.config.ts            # Vite 配置
│   ├── tsconfig.json             # TypeScript 配置
│   └── Dockerfile                # 前端容器镜像（Nginx）
│
├── docs/
│   └── expansion/
│       └── PHASE_7-16_EXPANSION_PLAN.md  # 未来功能路线图
│
├── scripts/
│   └── deploy.sh                 # 一键部署脚本
│
├── docker-compose.yml            # Docker Compose 编排配置
├── Dockerfile                   # 根目录 Dockerfile（多阶段构建）
├── DEPLOYMENT.md                # 详细部署指南
├── package.json                  # 根目录 Node 配置
├── playwright.config.ts         # Playwright E2E 测试配置
├── pytest.ini                   # Pytest 配置
├── requirements.txt             # 根目录 Python 依赖
└── README.md                    # 项目说明文档
```

---

## 技术栈

### 后端

| 分类 | 技术 | 用途 |
|------|------|------|
| Web 框架 | Django 5.x | HTTP 服务、Admin 后台、ORM |
| REST API | django-ninja | 异步 REST API（支持 Pydantic 验证）|
| AI 编排 | LangGraph 0.3.x | 工作流图、多模型、流式执行 |
| LLM 集成 | LangChain（OpenAI/Anthropic/Ollama）| 多模型支持 |
| 状态持久化 | DjangoSaver（MySQL）| LangGraph 检查点持久化 |
| WebSocket | Django Channels + Redis | 实时通信、流式响应 |
| 任务队列 | Celery + Redis | 异步任务调度（文档处理等）|
| 任务监控 | Flower | Celery 任务可视化监控 |
| 数据库 | MySQL 8.0 | 主数据存储 |
| 向量数据库 | ChromaDB | RAG 语义检索 |
| 文档解析 | PyMuPDF、python-docx、BeautifulSoup | PDF/Word/HTML 解析 |
| ASGI 服务器 | Daphne / Uvicorn | 支持异步与 WebSocket |
| 认证 | djangorestframework-simplejwt | JWT Token 认证 |

### 前端

| 分类 | 技术 | 用途 |
|------|------|------|
| 框架 | Vue 3.4 + Composition API | 响应式 UI |
| 语言 | TypeScript 5.4 | 类型安全 |
| 构建工具 | Vite 5.2 | 快速开发与生产构建 |
| 可视化编辑器 | @vue-flow/core | 节点编排画布 |
| UI 组件库 | Element Plus 2.6 | 快速 UI 开发 |
| 状态管理 | Pinia 2.1 | 轻量级状态管理 |
| 路由 | Vue Router 4.3 | SPA 路由 |
| HTTP 客户端 | Axios | API 请求 |
| 实时通信 | @microsoft/fetch-event-source | SSE 流式请求 |
| 图标 | @element-plus/icons-vue | Element Plus 图标集 |
| E2E 测试 | Playwright | 端到端测试 |

### 基础设施

| 分类 | 技术 | 用途 |
|------|------|------|
| 容器化 | Docker + Docker Compose | 服务编排 |
| 反向代理 | Nginx 1.25 | SPA 服务、API 代理 |
| 镜像构建 | 多阶段 Dockerfile | 优化镜像体积 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户浏览器                                     │
│            Vue 3 SPA (http://localhost)                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP / SSE / WebSocket
┌────────────────────────────▼────────────────────────────────────────┐
│                     Nginx (port 80 / 443)                            │
│         SPA 静态文件  │  /api/* → 后端  │  /ws/* → 后端             │
└──────┬─────────────────────┬──────────────────────┬────────────────┘
       │                     │                      │
  ┌────▼────┐          ┌─────▼──────┐        ┌─────▼──────┐
  │ Frontend │          │   Backend  │        │   Redis    │
  │(Nginx)   │          │  (Django   │        │ (Channels  │
  │ port:80  │          │   Daphne)  │        │  broker +  │
  └──────────┘          │  port:8000 │        │ Celery)    │
                         └─────┬──────┘        └─────┬──────┘
                               │                      │
                    ┌──────────▼──────────┐  ┌──────▼──────┐
                    │       MySQL          │  │  Celery     │
                    │   (persistent)      │  │  Workers    │
                    └─────────────────────┘  └─────────────┘
```

---

## 核心功能

### 工作流引擎（Phase 1-3）

- **并行执行** — LangGraph Send API 支持多分支并行内容生成
- **条件路由** — Router 节点根据意图分发到专业子分支
- **人机交互** — `interrupt()` + `Command(resume=True)` 支持人工审批节点
- **多模型切换** — OpenAI / Claude / Ollama 模型工厂
- **重试机制** — Tenacity 实现的指数退避重试
- **状态持久化** — DjangoSaver 将执行状态checkpoint存入MySQL

### 向量检索 RAG（Phase 8）

- 支持 PDF、Word、HTML 文档解析
- 多种分块策略（按段落、按 token 数）
- ChromaDB 向量存储与语义检索
- 可配置的 Embedding 模型（OpenAI / VectorEngine）

### 异步任务（Phase 9）

- Celery 任务队列处理文档上传、向量入库等耗时操作
- Flower 监控面板
- Celery Beat 定时任务调度
- 2 个 Worker 副本保证高可用

### 可观测性（Phase 10）

- 执行追踪（耗时、节点级耗时）
- LLM 成本追踪（token 消耗、API 调用费用）
- 执行成功率统计

### JWT 认证

- 用户注册 / 登录
- Token 刷新机制
- 会话管理

---

## 环境配置

### 快速配置（开发环境）

```bash
# 1. 后端环境变量
cp Backend/.env.example Backend/.env
# 编辑 Backend/.env，填入必要的配置（见下方详细说明）

# 2. 前端依赖
cd Frontend
npm install

# 3. 后端依赖
cd ../Backend
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# 4. 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 5. 创建超级用户
python manage.py createsuperuser

# 6. 启动后端
python manage.py runserver

# 7. 启动前端（新终端）
cd Frontend
npm run dev
```

### 环境变量详解

| 变量 | 说明 | 示例 |
|------|------|------|
| `SECRET_KEY` | Django 密钥 | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | 调试模式 | `True`（开发）/ `False`（生产）|
| `DATABASE_URL` | MySQL 连接字符串 | `mysql://flowly:password@localhost:3306/flowly_db` |
| `REDIS_URL` | Redis 连接字符串 | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-...` |
| `OPENAI_MODEL` | OpenAI 模型 | `gpt-4o` |
| `OPENAI_BASE_URL` | OpenAI API 地址 | `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | Anthropic API Key | `sk-ant-...`（可选）|
| `OLLAMA_BASE_URL` | Ollama 本地地址 | `http://localhost:11434`（可选）|
| `VECTORENGINE_API_KEY` | VectorEngine API Key | `sk-...`（可选）|
| `VECTORENGINE_BASE_URL` | VectorEngine API 地址 | `https://api.vectorengine.cn/v1` |
| `CORS_ALLOWED_ORIGINS` | CORS 允许的来源 | `http://localhost:5173` |
| `ALLOWED_HOSTS` | Django 允许的 Host | `localhost,127.0.0.1` |
| `CELERY_BROKER_URL` | Celery 消息队列 | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery 结果存储 | `redis://localhost:6379/1` |
| `LANGSMITH_TRACING` | 启用 LangSmith 追踪 | `true`（可选）|
| `LANGSMITH_API_KEY` | LangSmith API Key | `ls-...`（可选）|

---

## 启动服务

### 开发模式

```bash
# 后端（Django 开发服务器，端口 8000）
cd Backend
python manage.py runserver

# 前端（Vite 热更新，端口 5173）
cd Frontend
npm run dev
```

### Docker Compose（推荐用于开发与生产）

```bash
# 1. 配置环境变量
cp Backend/.env.example Backend/.env
# 编辑 Backend/.env

# 2. 启动所有服务
docker compose up -d --build

# 3. 应用数据库迁移
docker compose exec backend python manage.py migrate

# 4. 创建管理员账户
docker compose exec backend python manage.py createsuperuser

# 5. 访问应用
# 前端: http://localhost
# 后端 API: http://localhost:8000/api/
# Flower 监控: http://localhost:5555
```

> **说明**：Docker Compose 会启动以下服务：
> - `db` — MySQL 8.0（端口 3307）
> - `redis` — Redis 7（端口 6379）
> - `backend` — Django Daphne ASGI（端口 8000）
> - `celery_worker` — Celery Worker × 2 副本
> - `celery_beat` — Celery Beat 定时任务调度器
> - `flower` — Celery 监控面板（端口 5555）
> - `frontend` — Nginx 托管 Vue SPA（端口 80）

### 独立服务启动

```bash
# 仅后端 ASGI（支持 WebSocket）
daphne -b 0.0.0.0 -p 8000 flowly_backend.asgi:application

# 或使用 Uvicorn
uvicorn flowly_backend.asgi:application --host 0.0.0.0 --port 8000 --reload

# Celery Worker（后台任务）
celery -A flowly_backend worker --loglevel=info --concurrency=4

# Celery Beat（定时任务）
celery -A flowly_backend beat --loglevel=info
```

---

## API 接口

基础路径: `/api/`

### 工作流执行（WebSocket + SSE）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflows/run` | WebSocket | 创建并执行工作流 |
| `/api/workflows/resume` | POST | 人机交互节点恢复执行 |
| `/api/workflows/abort` | POST | 中止运行中的工作流 |

### 工作流 CRUD

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflows/` | GET | 获取工作流列表 |
| `/api/workflows/` | POST | 创建工作流定义 |
| `/api/workflows/{id}/` | GET | 获取工作流详情 |
| `/api/workflows/{id}/` | PUT | 更新工作流 |
| `/api/workflows/{id}/` | DELETE | 删除工作流 |

### 执行记录

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/executions/` | GET | 获取执行历史 |
| `/api/executions/{thread_id}/` | GET | 获取执行详情 |

### 认证

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/profile` | GET/PUT | 用户资料 |
| `/api/auth/refresh` | POST | 刷新 Token |

### RAG 知识库

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/documents/upload` | POST | 上传文档（异步处理）|
| `/api/documents/` | GET | 文档列表 |
| `/api/documents/search` | GET | 语义检索 |
| `/api/documents/{id}/` | DELETE | 删除文档 |

### Celery 任务

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/tasks/` | GET | 任务列表 |
| `/api/tasks/{task_id}/` | GET | 任务状态 |

### 可观测性分析

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analytics/overview` | GET | 总览统计 |
| `/api/analytics/executions` | GET | 执行趋势 |
| `/api/analytics/cost` | GET | 成本追踪 |
| `/api/analytics/performance` | GET | 性能分析 |

---

## 测试

### 后端单元测试

```bash
cd Backend

# 运行所有测试
pytest

# 运行指定测试
pytest tests/test_workflows.py

# 带覆盖率报告
pytest --cov=ai_engine --cov-report=html

# 查看 HTML 覆盖率报告
start htmlcov/index.html
```

### 前端 E2E 测试（Playwright）

```bash
# 安装 Playwright 浏览器
npx playwright install

# 运行 E2E 测试
cd Frontend
npx playwright test

# UI 模式（可视化调试）
npx playwright test --ui

# 单个测试文件
npx playwright test tests/dashboard.spec.ts
```

---

## 开发指南

### 添加新的 API 端点

在 `Backend/ai_engine/` 下创建新的 `*_api.py` 文件：

```python
from ninja import Router
from pydantic import BaseModel

router = Router()

class RequestSchema(BaseModel):
    field: str

class ResponseSchema(BaseModel):
    result: str

@router.post("/endpoint", response=ResponseSchema)
def my_endpoint(request, payload: RequestSchema):
    return {"result": f"processed: {payload.field}"}
```

然后在 `ai_engine/urls.py` 中注册路由：

```python
from .my_new_api import router as new_router
api.add_router("/new", new_router)
```

### 添加新的前端视图

1. 在 `Frontend/src/views/` 创建 `.vue` 文件
2. 在 `Frontend/src/router/index.ts` 中添加路由
3. 在 Pinia stores 中管理状态（如需要）

### 添加新的 LangGraph 节点

在 `Backend/ai_engine/workflow.py` 中：

```python
def my_node(state: WorkflowState) -> dict:
    """节点文档说明"""
    return {"result": {"key": "value"}}

# 在 build_graph() 中注册节点
workflow.add_node("my_node", my_node)
```

---

## 常见问题

**Q: Redis 连接失败？**  
确保 Redis 服务已启动（Docker Compose 自动启动），或检查 `REDIS_URL` 配置。

**Q: WebSocket 连接失败？**  
确认 Nginx 已正确配置 WebSocket 代理（`docker-compose.yml` 中已配置）。检查浏览器控制台是否有 CORS 错误。

**Q: 数据库迁移失败？**  
确认 MySQL 服务运行正常，检查 `DATABASE_URL` 格式是否正确。首次运行后：
```bash
python manage.py makemigrations
python manage.py migrate
```

**Q: OpenAI / Claude API 调用失败？**  
确认 API Key 正确配置，且网络可访问 `OPENAI_BASE_URL`。检查 `.env` 文件中的 `OPENAI_API_KEY` 和 `ANTHROPIC_API_KEY`。

**Q: 文档上传后无法检索？**  
RAG 处理是异步的（Celery 任务）。检查 `docker compose logs celery_worker` 确认文档处理任务正常执行。

**Q: 如何查看 Celery 任务队列？**  
访问 `http://localhost:5555` 查看 Flower 监控面板（默认用户名密码为空）。

**Q: 忘记管理员密码？**  
```bash
docker compose exec backend python manage.py changepassword admin
```

---

## 路线图

参见 [docs/expansion/PHASE_7-16_EXPANSION_PLAN.md](docs/expansion/PHASE_7-16_EXPANSION_PLAN.md)

已规划的后续阶段：

| 阶段 | 功能 |
|------|------|
| Phase 7 | 可视化编辑器升级（React Flow）|
| Phase 8 | 向量检索 & RAG（已完成）|
| Phase 9 | 异步任务队列 Celery（已完成）|
| Phase 10 | 可观测性面板（已完成）|
| Phase 11 | MCP 工具生态集成 |
| Phase 12 | 多模态处理（图像/音频）|
| Phase 13 | 安全与合规（RBAC、审计日志）|
| Phase 14 | LLMOps 部署管理 |
| Phase 15 | 测试与评估框架 |
| Phase 16 | 记忆与上下文管理 |

---

## 许可证

MIT License
