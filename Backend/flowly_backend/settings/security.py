"""安全与运行模式。"""

import os

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-this-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
raw_hosts = (os.getenv("ALLOWED_HOSTS", "*") or "*").strip()
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(",") if h.strip()]

# Railway healthcheck hits the service with this Host header.
# If it's not allowed, deployment fails with DisallowedHost.
if "*" not in ALLOWED_HOSTS and "healthcheck.railway.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("healthcheck.railway.app")
