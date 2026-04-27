#!/usr/bin/env sh
set -eu

# Railway/Render/Fly 等平台会注入 PORT；本地默认 8000
PORT="${PORT:-8000}"

# Quick diagnostics (no secrets): show which DB config is being used.
if [ -n "${DATABASE_URL:-}" ]; then
  echo "[boot] DATABASE_URL is set (length=${#DATABASE_URL})"
elif [ -n "${MYSQL_URL:-}" ]; then
  echo "[boot] MYSQL_URL is set (length=${#MYSQL_URL})"
elif [ -n "${MYSQL_PUBLIC_URL:-}" ]; then
  echo "[boot] MYSQL_PUBLIC_URL is set (length=${#MYSQL_PUBLIC_URL})"
else
  echo "[boot] DATABASE_URL/MYSQL_URL is NOT set; will try MYSQL* vars or fallback to sqlite"
fi
echo "[boot] MYSQLHOST=${MYSQLHOST:-<empty>} MYSQLPORT=${MYSQLPORT:-<empty>} MYSQLDATABASE=${MYSQLDATABASE:-<empty>} MYSQLUSER=${MYSQLUSER:-<empty>}"
echo "[boot] MYSQL_HOST=${MYSQL_HOST:-<empty>} MYSQL_PORT=${MYSQL_PORT:-<empty>} MYSQL_DATABASE=${MYSQL_DATABASE:-<empty>} MYSQL_USER=${MYSQL_USER:-<empty>}"

# Ensure database schema is ready (Railway uses ephemeral containers).
# This prevents "no such table" 500s on fresh deploys.
python manage.py migrate --noinput -v 2

exec daphne -b 0.0.0.0 -p "$PORT" flowly_backend.asgi:application

