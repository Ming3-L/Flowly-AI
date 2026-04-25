"""
批量导入 OpenSpeech 语音合成音色列表到数据库（AIModelVariant）。

默认读取仓库根目录下：
  - 语音合成1.0.txt  -> catalog_key = speech-doubao-tts
  - 语音合成2.0.txt  -> catalog_key = speech-doubao-tts-2

文件格式：CSV（逗号分隔），表头包含：
  Voice_Type,音色名称,推荐场景
"""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "从语音合成1.0/2.0.txt 导入音色到 AIModelVariant。"

    def handle(self, *args, **options):
        from ai_engine.models import AIModelCatalogEntry, AIModelVariant

        repo_root = Path(__file__).resolve().parents[4]
        jobs = [
            ("speech-doubao-tts", repo_root / "语音合成1.0.txt"),
            ("speech-doubao-tts-2", repo_root / "语音合成2.0.txt"),
        ]

        total = 0
        for catalog_key, fp in jobs:
            entry = AIModelCatalogEntry.objects.filter(catalog_key=catalog_key).first()
            if not entry:
                self.stdout.write(self.style.WARNING(f"跳过：未找到模型目录项 {catalog_key}"))
                continue
            if not fp.exists():
                self.stdout.write(self.style.WARNING(f"跳过：文件不存在 {fp}"))
                continue

            seen: set[str] = set()
            with fp.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vid = (row.get("Voice_Type") or row.get("voice_type") or "").strip()
                    if not vid:
                        continue
                    name = (row.get("音色名称") or "").strip()
                    scene = (row.get("推荐场景") or "").strip()
                    label = name or vid
                    config = {"scene": scene} if scene else {}
                    seen.add(vid)
                    AIModelVariant.objects.update_or_create(
                        model_entry_id=entry.id,
                        variant_id=vid,
                        defaults={
                            "kind": AIModelVariant.Kind.VOICE,
                            "label": label[:160],
                            "value": vid[:256],
                            "sort_order": 0,
                            "config": config,
                            "is_active": True,
                        },
                    )
                    total += 1

            # 清理：文件里已不存在的 voice variants
            if seen:
                AIModelVariant.objects.filter(
                    model_entry_id=entry.id,
                    kind=AIModelVariant.Kind.VOICE,
                ).exclude(variant_id__in=list(seen)).delete()

            self.stdout.write(self.style.SUCCESS(f"{catalog_key}: 导入 {len(seen)} 个音色"))

        self.stdout.write(self.style.SUCCESS(f"完成：共 upsert {total} 条"))

