"""画布节点：按 ``modelKey`` 解析 ``AIModelCatalogEntry``。"""

from __future__ import annotations

from typing import Any, Mapping

from ai_engine.models import AIModelCatalogEntry


def catalog_entry_for_model_key(config: Mapping[str, Any]) -> AIModelCatalogEntry | None:
    mk = str(config.get("modelKey") or config.get("model_key") or "").strip()
    if not mk:
        return None
    return AIModelCatalogEntry.objects.filter(catalog_key=mk, is_active=True).first()
