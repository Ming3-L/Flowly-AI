# Django 配置模块化说明

- **入口**：`DJANGO_SETTINGS_MODULE=flowly_backend.settings` 指向本包（不再使用单文件 `settings.py`）。
- **`.env`**：仍放在 **`Backend/.env`**，由 `paths.py` 在导入时加载。
- **子模块**：`security`、`features`、`database`、`cors`、`channels_conf`、`celery_conf`、`ai_providers` 等，各司其职。
