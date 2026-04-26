# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies (use Tsinghua mirror for China)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (use Tsinghua PyPI mirror)
COPY requirements.txt .
RUN pip install --break-system-packages --user -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# ─── Stage 2: Production ─────────────────────────────────────────────────────
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install runtime dependencies (no build tools needed, use Tsinghua mirror)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && useradd -m -u 1000 appuser \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy application code
COPY --chown=appuser:appuser manage.py .
COPY --chown=appuser:appuser ai_engine ai_engine/
COPY --chown=appuser:appuser accounts accounts/
COPY --chown=appuser:appuser flowly_backend flowly_backend/
COPY --chown=appuser:appuser start.sh ./start.sh

USER appuser

EXPOSE 8000

# Default: Daphne ASGI server (supports WebSocket + Channels)
CMD ["sh", "./start.sh"]
