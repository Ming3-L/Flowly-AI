# Flowly 免费优先上线（网站 + Electron）

本文目标：**尽量不使用 Docker**，把项目做成别人可用的“网站 + 桌面端（Electron）”。  
部署策略：**前端静态托管（免费平台） + 后端上 Railway（或同类）**，Electron 默认连接线上后端。

---

## 0. 关键结论（先说最重要的）

- **最省钱**：后端用 SQLite（不接付费 MySQL），Redis 先不启用或用免费 Redis（见下文）。
- **最稳上线**：后端服务只跑 **Django ASGI（Daphne）**；Celery/Beat/Flower 在免费方案里先不跑。
- **WebSocket**：如果不想依赖 Redis，可设置 `USE_INMEMORY_CHANNEL_LAYER=true`（单实例可用，适合 demo / 免费部署）。
- **前端/桌面端改域名无需重打包**：通过 `Frontend/public/runtime-config.js` 的 `API_BASE_URL` 运行时注入。

---

## 1) 后端部署到 Railway（不使用 Docker）

### 1.1 创建 Railway 项目并从 GitHub 导入

1. 在 Railway 新建 Project → **Deploy from GitHub Repo**
2. 选择本仓库
3. Service 选择使用默认的 **Railpack** 构建

> 仓库已提供 `railway.json`，默认 start command 会执行：`cd Backend && sh start.sh`  
> 并使用健康检查：`/health/`

### 1.2 Railway Service Variables（最低可用配置）

在 Railway 的 Variables 里添加（示例值按需替换）：

- `SECRET_KEY`: 用 Python 生成一个新的
- `DEBUG`: `False`
- `ALLOWED_HOSTS`: Railway 分配的域名（或 `*` 风险更高，不推荐）
- `DATABASE_URL`: **留空**（会自动回退 SQLite）
- `USE_INMEMORY_CHANNEL_LAYER`: `true`（免费方案先不接 Redis）
- `REDIS_URL`: 可留空（若你后续接 Redis 再填）
- `CORS_ALLOWED_ORIGINS`: 你的前端域名，例如 `https://flowly.pages.dev`

可选（至少配置一个）：

- `OPENAI_API_KEY` 或 `DOUBAO_API_KEY`/`ARK_API_KEY` 或 `ANTHROPIC_API_KEY`

生成 `SECRET_KEY`（本地执行一次即可）：

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 1.3 部署后自检

- 后端健康检查：访问 `https://<你的后端域名>/health/` 应返回 `status: healthy`

> 注意：免费方案使用 SQLite 时，**重启/重新部署可能丢数据**。要做“长期可用”，必须接外部数据库（通常会触发付费）。

---

## 2) 前端静态站（免费平台：Cloudflare Pages / Vercel / Netlify 任选）

## 2A) 前端静态站（GitHub Pages：你已选择）

> 本仓库已加入 GitHub Actions 工作流：`.github/workflows/deploy-pages.yml`  
> 推送到 `main/master` 后会自动构建 `Frontend/` 并发布到 GitHub Pages。

### 2A.1 在 GitHub 打开 Pages

1. 进入仓库 → **Settings** → **Pages**
2. Source 选择 **GitHub Actions**
3. 等待 Actions 跑完后，Pages 会给你一个站点地址

### 2A.2 设置后端地址（运行时注入，推荐）

GitHub Pages 是纯静态托管，最简单做法是直接改 `Frontend/public/runtime-config.js` 里的值后再推送：

```js
window.__FLOWLY_RUNTIME__ = { API_BASE_URL: "https://<你的后端域名>/api" }
```

> 说明：我们已经处理了 GitHub Pages 的 SPA 刷新 404 问题（`Frontend/public/404.html` + `index.html` 恢复路由）。

---

## 2B) 前端静态站（免费平台：Cloudflare Pages / Vercel / Netlify 任选）

### 2.1 构建设置

以 Cloudflare Pages 为例：

- **Root directory**: `Frontend`
- **Build command**: `npm ci && npm run build`
- **Build output directory**: `dist`

### 2.2 设置后端地址（两种方式）

#### 方式 A（推荐）：运行时注入（不需重新构建）

把静态站的 `runtime-config.js` 内容覆盖成：

```js
window.__FLOWLY_RUNTIME__ = { API_BASE_URL: "https://<你的后端域名>/api" }
```

你也可以在托管平台做“发布后替换文件”（不同平台方式不同）。

#### 方式 B：构建时注入（需要重新构建）

设置环境变量：

- `VITE_API_BASE_URL = https://<你的后端域名>/api`

---

## 3) Electron 桌面端（默认连接线上后端）

桌面端工程在 `Desktop/`。

### 3.1 打包前准备

先构建前端：

```bash
cd Frontend
npm ci
npm run build
```

### 3.2 开发运行 Electron

```bash
cd Desktop
npm ci

# 方式 1：通过环境变量指定后端（推荐）
set FLOWLY_API_BASE_URL=https://<你的后端域名>/api
npm run dev
```

也可以给最终用户提供一个配置文件（无需环境变量）：

- 文件位置：`%APPDATA%/Flowly/flowly.config.json`（Electron 的 userData 目录）
- 内容示例：

```json
{ "API_BASE_URL": "https://<你的后端域名>/api" }
```

### 3.3 生成安装包（Windows）

```bash
cd Desktop
npm run dist
```

产物在 `Desktop/release/`。

---

## 4) 免费方案的“现实限制”与升级路径

- **SQLite**：免费但不持久；想让用户长期使用，需要外部数据库（通常要付费）。
- **Redis/Celery**：
  - 免费 demo：先不跑 Celery，Channels 用 `USE_INMEMORY_CHANNEL_LAYER=true`
  - 要稳定 WebSocket、多实例、后台任务：再接 Redis，并增加一个 worker 服务（通常会增加成本）

