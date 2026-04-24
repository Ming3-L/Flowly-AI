"""
前端 UI 文案：从数据库读取，由管理员在 Django Admin 中维护。

GET /api/ui-labels/?locale=zh-CN  — 无需登录，供 SPA 启动时拉取整包键值。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db.models import Max
from django.http import HttpRequest
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]

from ai_engine.models import UILabel

router = Router(tags=["UI 文案"])


class UILabelsResponseSchema(Schema):
    locale: str
    labels: dict[str, str]
    updated_at: str | None = None


@router.get("/", response=UILabelsResponseSchema)
def get_ui_labels_bundle(request: HttpRequest, locale: str = "zh-CN"):
    """
    返回指定语言下所有**启用**的文案键值对，供前端一次性缓存。

    - ``locale``：BCP 47 风格，默认 ``zh-CN``。
    """
    loc = (locale or "zh-CN").strip() or "zh-CN"
    qs = UILabel.objects.filter(locale=loc, is_active=True).values("key", "value")
    labels: dict[str, str] = {row["key"]: row["value"] for row in qs}
    agg = UILabel.objects.filter(locale=loc, is_active=True).aggregate(m=Max("updated_at"))
    m = agg.get("m")
    updated_at = m.isoformat() if isinstance(m, datetime) else None
    return UILabelsResponseSchema(locale=loc, labels=labels, updated_at=updated_at)
