# Flowly AI — 部署指南（生产可用）

Production-ready deployment with Docker Compose.

---

## 前置条件

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+
- 至少配置一种可用的模型接入密钥（OpenAI / 豆包方舟 / Claude 等）

---

## 快速开始（Docker Compose）

```bash
# 1. Clone the repository
git clone https://github.com/your-org/flowly-ai.git
cd flowly-ai

# 2. Configure environment
cp Backend/.env.example Backend/.env
# 编辑 Backend/.env，至少需要：
# - SECRET_KEY（可用 python 生成）
# - DATABASE_URL（Docker 环境通常指向 db 容器）
# - REDIS_URL
# - 至少一个 AI 接入密钥（如 OPENAI_API_KEY 或 DOUBAO_API_KEY/ARK_API_KEY）

# 3. Start all services
docker compose up -d

# 4. Apply database migrations
docker compose exec backend python manage.py migrate

# 5. Create admin user
docker compose exec backend python manage.py createsuperuser

# 6. Open the app
open http://localhost
```

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (port 80)                       │
│   SPA Frontend  │  /api/* → Backend  │  /ws/* → Backend     │
└────────┬──────────────────┬──────────────────┬──────────────┘
         │                  │                  │
    ┌────▼────┐       ┌─────▼──────┐     ┌────▼────┐
    │Frontend │       │  Backend   │     │  Redis  │
    │(Vue SPA)│       │  (Django   │     │ (Channels│
    │ Nginx   │       │  Daphne)   │     │  broker)│
    └─────────┘       └─────┬──────┘     └─────────┘
                            │
                       ┌────▼────┐
                       │  MySQL  │
                       │   DB    │
                       └─────────┘
```

---

## 配置说明

### 环境变量（后端）

复制 `Backend/.env.example` 为 `Backend/.env` 并配置：

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Set to `False` in production | Yes |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | Yes |
| `DATABASE_URL` | MySQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API Key（可选：也可用豆包/Claude） | No |
| `OPENAI_MODEL` | Model to use | No (default: gpt-4o) |
| `ANTHROPIC_API_KEY` | Anthropic API key | No |
| `LANGSMITH_TRACING` | Enable LangSmith tracing | No |

### Database

MySQL 8.0 is used for persistent storage. The schema is managed by Django migrations:

```bash
# Run migrations
docker compose exec backend python manage.py migrate

# Create a new migration after model changes
docker compose exec backend python manage.py makemigrations

# Load fixtures
docker compose exec backend python manage.py loaddata fixtures/*.json
```

---

## 服务列表

### Backend (Django + Daphne ASGI)

- **Port:** 8000 (internal)
- **Runs:** Daphne ASGI server (WebSocket + Channels support)
- **Entry:** `flowly_backend.asgi:application`
- **Health check:** `curl -f http://localhost:8000/api/` or check Daphne process

### Frontend (Vue 3 + Nginx)

- **Port:** 80 (external)
- **Build:** Vite production build
- **Serves:** Vue SPA with client-side routing

### Nginx Reverse Proxy

Handles:
- Static file serving (Vue build artifacts)
- API proxy to Django (`/api/*`)
- WebSocket proxy to Django (`/ws/*`)
- SPA fallback routing

### MySQL 8.0

- **Port:** 3306 (external, optional)
- **Volume:** `mysql_data` (persistent)
- **Health check:** `mysqladmin ping`

### Redis 7

- **Port:** 6379 (external, optional)
- **Volume:** `redis_data` (persistent)
- **Purpose:** Django Channels message broker
- **Purpose:** Django Channels broker + Celery broker/backend（默认使用不同 DB：0/1）
- **Health check:** `redis-cli ping`

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Development/Small Scale)

```bash
docker compose up -d --build
```

### Option 2: Docker Stack (Swarm Mode)

```bash
docker stack deploy -c docker-compose.yml flowly
```

### Option 3: Kubernetes

Convert `docker-compose.yml` to Kubernetes manifests using [Kompose](https://kompose.io/):

```bash
kompose convert
kubectl apply -f ./
```

### Option 4: Cloud Providers

| Provider | Recommended Service |
|----------|---------------------|
| AWS | ECS + RDS + ElastiCache |
| GCP | Cloud Run + Cloud SQL + Memorystore |
| Azure | Container Apps + Azure Database |
| Railway | One-click deployment |

---

## Production Checklist

Before going live:

- [ ] Set `DEBUG=False` in environment
- [ ] Use a strong `SECRET_KEY` (regenerate, not the default)
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Use HTTPS (put Nginx behind a TLS terminator or use Traefik)
- [ ] Set up MySQL backup strategy
- [ ] Configure Redis persistence (AOF recommended)
- [ ] Set up monitoring (Prometheus + Grafana recommended)
- [ ] Configure log aggregation
- [ ] Set up rate limiting on the API
- [ ] Review CORS settings
- [ ] 若启用 Celery Beat：确认定时任务已启动（包含 90 天 generated 资源清理）

## 定时任务说明（Celery Beat）

项目在 `Backend/flowly_backend/celery.py` 中配置了 Beat 定时任务，包括：

- `cleanup_failed_executions`：清理失败执行记录（默认 7 天）
- `retry_stale_executions`：标记超时 running 的执行
- `warm_workflow_cache`：预热工作流缓存
- `cleanup_generated_media_assets`：清理 90 天前 `MEDIA_ROOT/generated/...` 本地生成资源，避免磁盘无限增长

如果你不运行 `celery -A flowly_backend beat`，上述周期任务不会执行；你也可以手动运行：

```bash
python Backend/manage.py cleanup_generated_media_assets --dry-run --days 90
```

---

## HTTPS Setup (with Traefik)

```yaml
# docker-compose.prod.yml
services:
  traefik:
    image: traefik:v3.0
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./certs:/certs
    command:
      - "--certificatesresolvers.letsencrypt.acme.email=you@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/certs/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=http"
```

---

## Scaling

### Horizontal Scaling (Backend)

Backend services are stateless and can be scaled:

```bash
# Scale to 3 backend instances
docker compose up -d --scale backend=3
```

**Note:** When scaling Daphne, configure a shared Redis connection for Channels. Each Daphne worker handles WebSocket connections independently.

### Database

For production, use a managed database service:
- AWS RDS MySQL 8.0
- GCP Cloud SQL
- PlanetScale (MySQL-compatible serverless)
- Aiven MySQL

### Caching

Redis can be clustered for high availability:
```bash
docker compose -f docker-compose.yml -f docker-compose.cluster.yml up -d
```

---

## Monitoring

### Health Checks

All services have built-in health checks:

```bash
# Check service health
docker compose ps

# View logs
docker compose logs -f backend

# Check individual service
docker compose exec backend python manage.py health_check
```

### Metrics

Integrate with Prometheus for metrics collection:

```python
# Backend: Add prometheus_client
pip install django-prometheus
```

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker compose logs backend

# Common issues:
# 1. MySQL not ready — wait for health check
# 2. Missing migrations — run: docker compose exec backend python manage.py migrate
# 3. Wrong DATABASE_URL — check format
```

### WebSocket connection fails

```bash
# Verify Redis is accessible from backend
docker compose exec backend python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Check Nginx WebSocket proxy config
docker compose exec frontend cat /etc/nginx/conf.d/default.conf
```

### Frontend shows 502

```bash
# Backend might be starting up
docker compose logs backend

# Or backend might be crashing — check for import errors
docker compose exec backend python -c "from flowly_backend.asgi import application; print('OK')"
```

### Database migrations fail

```bash
# Check MySQL is running
docker compose exec db mysqladmin ping -h localhost

# Connect to MySQL directly
docker compose exec db mysql -u root -p
```

---

## Updating

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose up -d --build

# Run migrations
docker compose exec backend python manage.py migrate
```

---

## Backup

### MySQL Backup

```bash
# Full backup
docker compose exec db mysqldump -u root -p flowly_db > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T db mysql -u root -p flowly_db < backup_20240101.sql
```

### Volume Backup

```bash
docker run --rm -v flowly_db_mysql_data:/data -v $(pwd):/backup alpine tar czf /backup/mysql_backup.tar.gz /data
```
