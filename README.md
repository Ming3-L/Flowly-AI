# Flowly AI Backend

基于 Django + LangGraph 的 AI 工作流引擎后端服务。

## 项目结构

```
Backend/
├── requirements.txt          # Python 依赖
├── manage.py                 # Django 管理脚本
├── .env                      # 环境变量（本地配置，不提交）
├── .env.example              # 环境变量模板
├── flowly_backend/           # Django 项目配置
│   ├── __init__.py
│   ├── settings.py           # 核心配置文件
│   ├── urls.py               # 路由配置
│   ├── asgi.py              # ASGI 配置（支持 WebSocket）
│   └── wsgi.py             # WSGI 配置
└── ai_engine/               # AI 引擎应用
    ├── __init__.py
    ├── apps.py
    ├── models.py             # 数据模型
    ├── api.py               # Django Ninja REST API
    ├── views.py
    ├── urls.py               # API 路由
    ├── admin.py
    └── workflow.py           # LangGraph 工作流引擎
```

## 技术栈

| 分类 | 技术 | 用途 |
|------|------|------|
| Web 框架 | Django 5.x | HTTP 服务、Admin 后台 |
| REST API | django-ninja | 异步 REST API |
| 数据库 | MySQL / SQLite | 数据持久化 |
| AI 框架 | LangChain + LangGraph | 工作流编排与 LLM 调用 |
| WebSocket | Django Channels + Redis | 实时通信 |
| ASGI 服务器 | Daphne / Uvicorn | 支持异步与 WebSocket |

## 环境配置

### 1. 创建虚拟环境

```bash
cd Backend
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，或直接编辑 `.env`：

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
# MySQL（生产环境）
DATABASE_URL=mysql://user:password@localhost:3306/flowly_db
# SQLite（开发环境，默认）
DATABASE_URL=

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# AI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1

# CORS Settings
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> **安全提示**: `SECRET_KEY` 和 `OPENAI_API_KEY` 等敏感信息不要提交到代码仓库。

### 4. 数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. 创建超级用户（如需访问 Admin）

```bash
python manage.py createsuperuser
```

## 启动服务

### 开发模式（HTTP）

```bash
python manage.py runserver
```

服务运行在 `http://localhost:8000`

### 生产模式（ASGI + WebSocket）

```bash
daphne -b 0.0.0.0 -p 8000 flowly_backend.asgi:application
```

### 使用 Uvicorn

```bash
uvicorn flowly_backend.asgi:application --host 0.0.0.0 --port 8000 --reload
```

## API 接口

基础路径: `/api/ai/`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/execute` | 执行 AI 工作流 |
| GET | `/api/ai/status/{thread_id}` | 查询工作流执行状态 |

### POST /api/ai/execute

**请求体:**

```json
{
  "query": "用户查询内容",
  "context": {
    "key": "value"
  }
}
```

**响应:**

```json
{
  "thread_id": "uuid",
  "status": "completed",
  "result": {
    "query": "...",
    "response": "AI 响应",
    "context": {}
  },
  "error": null
}
```

### GET /api/ai/status/{thread_id}

**响应:**

```json
{
  "thread_id": "uuid",
  "status": "completed",
  "messages": [],
  "metadata": {}
}
```

## 工作流引擎

`ai_engine/workflow.py` 使用 LangGraph 构建工作流图：

```
process_query → execute_workflow → format_response
```

- **process_query**: 解析用户查询，提取意图
- **execute_workflow**: 根据意图执行对应工作流
- **format_response**: 格式化最终响应

## 依赖说明

### 核心依赖

- `Django>=5.0` — Web 框架
- `django-ninja>=1.0.0` — 异步 REST API
- `langgraph>=0.2.0` — AI 工作流编排
- `langchain-openai>=0.2.0` — OpenAI LLM 集成

### 数据库

- `mysqlclient>=2.2.0` — MySQL 驱动（生产环境）
- `PyMySQL>=1.1.0` — MySQL 纯 Python 驱动备选

### 实时通信

- `channels>=4.0.0` — WebSocket 支持
- `channels-redis>=4.2.0` — Redis 消息层
- `daphne>=4.0.0` — ASGI 服务器

## 常见问题

**Q: Redis 连接失败？**  
确保 Redis 服务已启动，或在 `.env` 中配置正确的 `REDIS_URL`。

**Q: 数据库连接错误？**  
检查 `.env` 中 `DATABASE_URL` 配置，或确认 MySQL 服务运行正常。

**Q: OpenAI API 调用失败？**  
确认 `OPENAI_API_KEY` 正确配置，且网络可以访问 `OPENAI_BASE_URL`。
