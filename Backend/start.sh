#!/usr/bin/env sh
set -eu

# Railway/Render/Fly 等平台会注入 PORT；本地默认 8000
PORT="${PORT:-8000}"

# Ensure database schema is ready (Railway uses ephemeral containers).
# This prevents "no such table" 500s on fresh deploys.
python manage.py migrate --noinput

exec daphne -b 0.0.0.0 -p "$PORT" flowly_backend.asgi:application

