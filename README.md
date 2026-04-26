# Flowly AI

<!-- Markdown lint disable for inline HTML shields -->
[![Stars](https://img.shields.io/github/stars/yuxiaopao/Flowly-AI?style=social)](https://github.com/yuxiaopao/Flowly-AI)
[![License](https://img.shields.io/github/license/yuxiaopao/Flowly-AI)](https://github.com/yuxiaopao/Flowly-AI/blob/master/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4-green.svg)](https://vuejs.org/)
[![Django](https://img.shields.io/badge/Django-5.x-teal.svg)](https://www.djangoproject.com/)

> 基于 **Django + LangGraph + Vue 3** 的企业级 AI 工作流引擎，支持可视化编排、实时流式响应、向量检索与异步任务处理。

[English](README_en.md) · [快速开始](#快速上手) · [文档](#目录) · [路线图](#路线图) · [贡献](#贡献) · [MIT License](#许可证)

---

## ✨ 特性亮点

| 功能 | 说明 |
|------|------|
| 🎨 **可视化编辑器** | 基于 Vue Flow 的拖拽式节点编排，所见即所得 |
| 🔀 **LangGraph 引擎** | 并行执行、条件路由、人机交互、多模型动态切换 |
| ⚡ **实时流式响应** | Django Channels + WebSocket 驱动的 SSE 输出，毫秒级延迟 |
| 🔍 **RAG 向量检索** | PDF/Word/HTML 解析 + ChromaDB 语义搜索 |
| 📋 **异步任务队列** | Celery + Redis 后台任务调度，Flower 监控面板 |
| 🧹 **生命周期清理** | 自动清理 90 天前 `generated/` 本地资源，避免磁盘无限增长 |
| 📊 **可观测性面板** | 执行追踪、LLM 成本分析、性能监控 |
| 💾 **工作流持久化** | MySQL 事务同步 + DjangoSaver 检查点，失败自动回滚 |
| 🧩 **自定义节点** | 通过 API 注册模板节点类型，按节点粒度计费 |

---

## 🎯 快速上手

> 如果只需要在本地运行项目（不使用 Docker），请参考下方「数据库配置（本地部署）」章节，选择适合你的方案（MySQL 或 SQLite）。

### 本地开发

### 本地开发

```bash
# 后端
cd Backend
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# 前端（新终端）
cd Frontend
npm install
npm run dev
```

---

## 📷 界面预览

### 工作流编辑器

![工作流编辑器](./image/image.png)

基于 Vue Flow 构建的可视化工作流编辑器，支持拖拽编排、节点连接、实时预览。

### 可观测性面板

![可观测性面板](./image/e04212b5-9164-4423-b8c4-255d864e15bb.png)

实时追踪工作流执行状态，监控 LLM 调用成本与性能指标。

---

## 📁 目录结构

```
Flowly-AI/
├── Backend/                        # Django 后端
│   ├── ai_engine/                 # AI 引擎应用
│   │   ├── workflow.py            # LangGraph 工作流核心
│   │   ├── workflows.py           # 工作流 CRUD API
│   │   ├── executions.py          # 执行历史与统计
│   │   ├── api.py                 # Django Ninja REST API
│   │   ├── rag_api.py             # RAG / 向量检索 API
│   │   ├── rag_models.py          # Document / Chunk 数据模型
│   │   ├── task_api.py           # Celery 任务管理 API
│   │   ├── analytics_api.py      # 可观测性分析 API
│   │   ├── analytics_models.py    # 执行记录/成本追踪模型
│   │   ├── vector_store.py       # ChromaDB 向量存储封装
│   │   ├── document_processor.py  # PDF/Word 文档处理
│   │   ├── chunker.py            # 文档分块策略
│   │   ├── tasks.py              # Celery 异步任务定义
│   │   ├── cost_tracker.py       # LLM 成本追踪
│   │   ├── auth.py               # JWT 认证工具
│   │   ├── consumers.py          # Django Channels WebSocket 消费者
│   │   ├── graphs/               # LangGraph 子图定义
│   │   ├── conversation/         # AI 对话编排（预留）
│   │   ├── integrations/         # 外部服务配置
│   │   ├── workflow_graph/       # 工作流图 MySQL 规范化存储
│   │   ├── workflow_nodes/       # 节点类型占位
│   │   ├── migrations/           # 数据库迁移
│   │   └── models.py             # 数据模型
│   ├── accounts/                  # 用户认证应用
│   ├── checkpoint/               # LangGraph 状态持久化
│   ├── flowly_backend/           # Django 项目配置
│   │   ├── settings.py          # 核心配置
│   │   ├── urls.py              # 根路由
│   │   ├── asgi.py             # ASGI 应用（支持 WebSocket）
│   │   └── wsgi.py             # WSGI 应用
│   ├── manage.py                # Django 管理脚本
│   ├── requirements.txt         # Python 依赖
│   ├── Dockerfile               # 后端容器镜像
│   └── .env.example            # 环境变量模板
│
├── Frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── views/               # 页面视图
│   │   ├── components/         # 组件（WorkflowEditor/WorkflowMonitor 等）
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── router/             # Vue Router 配置
│   │   ├── types/             # TypeScript 类型定义
│   │   ├── modules/           # 领域模块（workflow/ai-conversation）
│   │   ├── utils/             # 工具函数
│   │   ├── styles/             # 全局样式
│   │   ├── assets/             # 静态资源
│   │   ├── App.vue            # 根组件
│   │   └── main.ts           # 应用入口
│   ├── package.json            # Node 依赖
│   ├── vite.config.ts         # Vite 配置
│   └── Dockerfile             # 前端容器镜像（Nginx）
│
├── docs/expansion/              # 功能路线图
├── scripts/deploy.sh           # 一键部署脚本
├── docker-compose.yml          # Docker Compose 编排
├── Dockerfile                  # 根目录多阶段构建
├── DEPLOYMENT.md              # 详细部署指南
├── pytest.ini                 # Pytest 配置
├── playwright.config.ts       # Playwright E2E 测试配置
└── requirements.txt          # 根目录 Python 依赖
```

---

## 🛠️ 技术栈

### 后端

| 分类 | 技术 | 用途 |
|------|------|------|
| Web 框架 | Django 5.x | HTTP 服务、Admin 后台、ORM |
| REST API | django-ninja | 异步 REST API（Pydantic 验证）|
| AI 编排 | LangGraph 0.3.x | 工作流图、多模型、流式执行 |
| LLM 集成 | LangChain（OpenAI / Anthropic / Ollama）| 多模型支持 |
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
| E2E 测试 | Playwright | 端到端测试 |

### 基础设施

| 分类 | 技术 | 用途 |
|------|------|------|
| 容器化 | Docker + Docker Compose | 服务编排 |
| 反向代理 | Nginx 1.25 | SPA 服务、API 代理 |
| 镜像构建 | 多阶段 Dockerfile | 优化镜像体积 |

---

## 🏗️ 系统架构

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

## 🔧 核心功能

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

## ⚙️ 环境配置

> 💡 **提示**：如果只需要在本地运行项目（不使用 Docker），请直接参考「快速上手」中的本地开发步骤，或参考下方「数据库配置（本地部署）」章节选择 MySQL 或 SQLite。

### 环境变量详解

AI 密钥除下表所列环境变量外，还可放在 **`Backend/ai_engine/integrations/project_secrets_local.py`**（从同目录 `project_secrets_local.example.py` 复制；该文件已加入 `.gitignore`）。代码中通过 `get_ai_provider_settings()` 统一获取。

| 变量 | 说明 | 示例 |
|------|------|------|
| `SECRET_KEY` | Django 密钥 | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | 调试模式 | `True`（开发）/ `False`（生产）|
| `DATABASE_URL` | MySQL 连接字符串 | `mysql://flowly:password@localhost:3306/flowly_db` |
| `MYSQL_ROOT_PASSWORD` | MySQL Root 密码（仅 Docker Compose） | `rootpassword` |
| `MYSQL_DATABASE` | MySQL 数据库名 | `flowly_db` |
| `MYSQL_USER` | MySQL 用户名 | `flowly` |
| `MYSQL_PASSWORD` | MySQL 用户密码 | `flowly_password` |
| `REDIS_URL` | Redis 连接字符串 | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-...` |
| `OPENAI_MODEL` | OpenAI 模型 | `gpt-4o` |
| `OPENAI_BASE_URL` | OpenAI API 地址 | `https://api.openai.com/v1` |
| `DOUBAO_API_KEY` / `ARK_API_KEY` | 火山方舟 / 豆包（二选一） | 勿提交仓库；泄露请轮换 |
| `DOUBAO_ARK_BASE_URL` | 方舟 OpenAI 兼容根路径 | 默认 `https://ark.cn-beijing.volces.com/api/v3` |
| `DOUBAO_ARK_MODEL` | 推理接入点（多为 `ep-...`） | 控制台 endpoint id |
| `FLOWLY_USE_DOUBAO_DEFAULT` | 已配置豆包密钥时是否将路由 `openai` 默认走方舟 | `1`（默认）或 `0` |
| `ANTHROPIC_API_KEY` | Anthropic API Key | `sk-ant-...`（可选）|
| `OLLAMA_BASE_URL` | Ollama 本地地址 | `http://localhost:11434`（可选）|
| `VECTORENGINE_API_KEY` | VectorEngine API Key | `sk-...`（可选）|
| `VECTORENGINE_BASE_URL` | VectorEngine API 地址 | `https://api.vectorengine.cn/v1` |
| `CORS_ALLOWED_ORIGINS` | CORS 允许的来源 | `http://localhost:5173` |
| `ALLOWED_HOSTS` | Django 允许的 Host | `localhost,127.0.0.1` |
| `CELERY_BROKER_URL` | Celery 消息队列 | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery 结果存储 | `redis://localhost:6379/1` |
### 生命周期清理（generated 资源）

项目会把部分“生成类”的图片/音频/视频等资源写入 `MEDIA_ROOT/generated/...`（同时在 `LocalMediaAsset` 表落库元数据）。
为避免磁盘无限增长，已内置 **90 天清理策略**：

- 定时任务：Celery Beat 每天执行一次（见 `Backend/flowly_backend/celery.py`）
- 手动执行（先 dry-run）：

```bash
python Backend/manage.py cleanup_generated_media_assets --dry-run --days 90
```

| `LANGSMITH_TRACING` | 启用 LangSmith 追踪 | `true`（可选）|
| `LANGSMITH_API_KEY` | LangSmith API Key | `ls-...`（可选）|

---

## 🚀 启动服务

### 开发模式

```bash
# 后端（Django 开发服务器，端口 8000）
cd Backend
python manage.py runserver

# 前端（Vite 热更新，端口 5173）
cd Frontend
npm run dev
```

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

## 🔌 API 接口

基础路径: `/api/`

### 工作流执行（WebSocket + SSE）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflows/run` | WebSocket | 创建并执行工作流 |
| `/api/workflows/canvas-node/run` | POST | 同步执行单个画布节点（写 CostRecord，含 client_node_id） |
| `/api/tasks/run/async` | POST | Celery 排队执行；`input_data` 含 `query`、`context`、`client_node_id`、`model_name`、`parallel_branches` |
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

## 🧪 测试

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

## 🛠️ 开发指南

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

## ❓ 常见问题

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

**Q: 提示 "Access denied for user" 或 "Unknown database"？**

检查 `Backend/.env` 中的 `DATABASE_URL` 是否与 MySQL 中创建的数据库和用户一致。Docker 环境中应使用 `db` 作为主机名，本地环境应使用 `localhost`。

**Q: 没有安装 MySQL，能否运行项目？**

可以。将 `Backend/.env` 中的 `DATABASE_URL` 留空或设为 `sqlite:///db.sqlite3`，Django 会自动使用 SQLite 数据库，无需安装 MySQL。

**Q: 如何连接本地已有的 MySQL 数据库？**

在 `Backend/.env` 中修改 `DATABASE_URL`，格式为 `mysql://用户名:密码@localhost:端口/数据库名`。确保 MySQL 已启动且用户权限配置正确。

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

## 💾 数据库配置（本地部署）

本节专门针对**将项目部署到本地**的用户，详细说明如何配置数据库。

### 数据库配置文件位置

| 配置文件 | 路径 | 说明 |
|---------|------|------|
| 环境变量配置 | `Backend/.env` | 数据库连接信息的核心配置 |
| Django 数据库配置 | `Backend/flowly_backend/settings.py` | 读取 `.env` 中的 `DATABASE_URL` |
| Docker Compose 配置 | `docker-compose.yml` | Docker 部署时的 MySQL 服务配置 |
| 环境变量模板 | `Backend/.env.example` | 配置项参考文档 |

### 数据库配置详解

项目支持两种数据库模式：

#### 模式一：MySQL（推荐，用于生产环境）

默认使用 MySQL 8.0，连接信息通过 `DATABASE_URL` 环境变量配置。

**配置格式：**
```
DATABASE_URL=mysql://用户名:密码@主机:端口/数据库名
```

**示例（Docker Compose 环境）：**
```
DATABASE_URL=mysql://flowly:flowly_password@db:3306/flowly_db
```

**示例（本地独立 MySQL）：**
```
DATABASE_URL=mysql://flowly:flowly_password@localhost:3307/flowly_db
```

#### 模式二：SQLite（用于开发环境）

如果无法连接 MySQL，可切换到 SQLite。Django 会自动在 `Backend/` 目录下创建 `db.sqlite3` 文件。

**配置方法：**
```bash
# 在 Backend/.env 中，将 DATABASE_URL 设为空或以 sqlite 开头
DATABASE_URL=sqlite:///db.sqlite3
# 或者直接注释掉 DATABASE_URL 行，Django 会默认使用 SQLite
```

### 本地部署数据库配置步骤

#### 方案 A：本地已安装 MySQL

如果你的机器上已经安装了 MySQL 8.0，可以直接连接本地数据库。

```bash
# 1. 在 MySQL 中创建数据库和用户
mysql -u root -p

# 在 MySQL 命令行中执行：
CREATE DATABASE flowly_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'flowly'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON flowly_db.* TO 'flowly'@'localhost';
FLUSH PRIVILEGES;

# 2. 编辑 Backend/.env，修改 DATABASE_URL
# 如果 MySQL 使用默认端口 3306：
DATABASE_URL=mysql://flowly:your_password@localhost:3306/flowly_db

# 3. 安装后端依赖
cd Backend
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# 4. 执行数据库迁移
python manage.py migrate

# 5. 创建超级用户
python manage.py createsuperuser

# 6. 启动后端
python manage.py runserver

# 7. 启动前端（新终端窗口）
cd Frontend
npm install
npm run dev
```

#### 方案 B：使用 SQLite（最简开发环境）

如果不想安装 MySQL，可以使用 SQLite。

```bash
# 1. 编辑 Backend/.env，将 DATABASE_URL 设为空或注释掉
# DATABASE_URL=

# 2. 安装依赖
cd Backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 3. Django 会自动使用 SQLite，创建 db.sqlite3 文件
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# 4. 启动前端
cd Frontend
npm install
npm run dev
```

### 常见数据库问题排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| `Access denied for user` | 用户名或密码错误 | 检查 `DATABASE_URL` 中的用户名密码是否与 MySQL 中创建的一致 |
| `Unknown database` | 数据库不存在 | 登录 MySQL 执行 `CREATE DATABASE flowly_db;` |
| `Can't connect to MySQL server` | MySQL 服务未启动或端口错误 | 确认 MySQL 运行中；检查端口是否与 `DATABASE_URL` 匹配 |
| `Connection refused` | 防火墙阻止或 MySQL 未监听该端口 | 检查 MySQL 配置文件 `my.cnf`，确认 `bind-address=0.0.0.0` |
| 迁移报错 `no such table` | 迁移未执行 | 运行 `python manage.py migrate` |
| 迁移报错 `table already exists` | 数据库已有旧数据 | 可选：删除数据库重新创建，或检查是否已执行过迁移 |

### 修改数据库配置后

修改 `Backend/.env` 中的 `DATABASE_URL` 后，本地重启 Django 服务器
  ```bash
  # Ctrl+C 停止后，重新运行
  python manage.py runserver
  ```

### 数据持久化说明

| 部署方式 | 数据存储位置 | 持久化方式 |
|---------|------------|----------|
| Docker Compose | MySQL 容器内 `/var/lib/mysql` + Docker Volume `mysql_data` | Docker Volume 自动持久化 |
| 本地 MySQL | MySQL 数据目录（`my.cnf` 中配置） | 依赖 MySQL 数据目录配置 |
| SQLite | `Backend/db.sqlite3` | 手动备份文件 |

---

## 🗺️ 路线图

已规划的后续阶段（详见 [docs/expansion/PHASE_7-16_EXPANSION_PLAN.md](docs/expansion/PHASE_7-16_EXPANSION_PLAN.md)）：

| 阶段 | 功能 | 状态 |
|------|------|------|
| Phase 7 | 可视化编辑器升级 | 🔄 进行中 |
| Phase 8 | 向量检索 & RAG | ✅ 已完成 |
| Phase 9 | 异步任务队列 Celery | ✅ 已完成 |
| Phase 10 | 可观测性面板 | ✅ 已完成 |
| Phase 11 | MCP 工具生态集成 | 📋 规划中 |
| Phase 12 | 多模态处理（图像/音频）| 📋 规划中 |
| Phase 13 | 安全与合规（RBAC、审计日志）| 📋 规划中 |
| Phase 14 | LLMOps 部署管理 | 📋 规划中 |
| Phase 15 | 测试与评估框架 | 📋 规划中 |
| Phase 16 | 记忆与上下文管理 | 📋 规划中 |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'feat: add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

提交前请确保：
- 代码通过 lint 检查
- 新功能附有测试用例
- Commit 符合 [Conventional Commits](https://www.conventionalcommits.org/) 规范

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。
